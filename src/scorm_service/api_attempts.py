
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from scorm_service.db import phien_lam_viec
from scorm_service.models import (
    Attempt,
    AttemptScoState,
    Enrollment,
    PackageVersion,
    Person,
    Sco,
    Section,
    SectionPackage,
)
from scorm_service.runtime import tao_cmi_mac_dinh

router = APIRouter(prefix="/api/v1", tags=["attempts"])


def lay_person_code(request: Request) -> str:
    """Lay person_code cua nguoi dung da dang nhap."""
    if not request.session.get("authenticated"):
        raise HTTPException(status_code=401, detail="Chua dang nhap")

    person_code = request.session.get("person_code")
    if not person_code:
        raise HTTPException(status_code=401, detail="Phien dang nhap khong hop le")

    return person_code


def kiem_tra_giang_vien(section_code: str, person_code: str) -> None:
    """Kiem tra giang vien co quyen quan ly section."""
    with phien_lam_viec() as s:
        person = s.get(Person, person_code)
        if person is None or person.person_type != "staff":
            raise HTTPException(status_code=403, detail="Khong co quyen giang vien")

        enrollment = s.scalar(
            select(Enrollment).where(
                Enrollment.section_code == section_code,
                Enrollment.person_code == person_code,
                Enrollment.role.in_(["teacher", "editingteacher"]),
                Enrollment.status == "registered",
            )
        )
        if enrollment is None:
            raise HTTPException(
                status_code=403,
                detail="Ban khong co quyen quan ly lop hoc phan nay",
            )

@router.post("/sections/{section_code}/packages/{package_version_id}")
def gan_goi(
    section_code: str,
    package_version_id: int,
    request: Request,
):
    """Gan mot phien ban SCORM vao lop hoc phan."""
    person_code = lay_person_code(request)
    kiem_tra_giang_vien(section_code, person_code)

    with phien_lam_viec() as s:
        section = s.get(Section, section_code)
        if section is None:
            raise HTTPException(status_code=404, detail="Khong tim thay lop hoc phan")

        package_version = s.get(PackageVersion, package_version_id)
        if package_version is None:
            raise HTTPException(status_code=404, detail="Khong tim thay goi SCORM")

        if package_version.status != "ready":
            raise HTTPException(
                status_code=409,
                detail="Phien ban goi SCORM chua san sang",
            )

        lien_ket = s.get(
            SectionPackage,
            (section_code, package_version_id),
        )

        if lien_ket is None:
            s.add(
                SectionPackage(
                    section_code=section_code,
                    package_version_id=package_version_id,
                )
            )

    return {
        "message": "Gan goi SCORM thanh cong",
        "section_code": section_code,
        "package_version_id": package_version_id,
    }


@router.get("/sections/{section_code}/packages")
def danh_sach_goi(section_code: str, request: Request):
    """Lay danh sach goi SCORM duoc gan vao lop."""
    person_code = lay_person_code(request)

    with phien_lam_viec() as s:
        section = s.get(Section, section_code)
        if section is None:
            raise HTTPException(status_code=404, detail="Khong tim thay lop hoc phan")

        enrollment = s.scalar(
            select(Enrollment).where(
                Enrollment.section_code == section_code,
                Enrollment.person_code == person_code,
                Enrollment.status == "registered",
            )
        )
        if enrollment is None:
            raise HTTPException(
                status_code=403,
                detail="Ban khong co quyen xem goi SCORM cua lop nay",
            )

        ket_qua = s.execute(
            select(PackageVersion)
            .join(
                SectionPackage,
                SectionPackage.package_version_id == PackageVersion.id,
            )
            .where(SectionPackage.section_code == section_code)
            .order_by(PackageVersion.package, PackageVersion.version)
        ).scalars().all()

        return {
            "section_code": section_code,
            "total": len(ket_qua),
            "packages": [
                {
                    "id": goi.id,
                    "package": goi.package,
                    "version": goi.version,
                    "scorm_version": goi.scorm_version,
                    "status": goi.status,
                }
                for goi in ket_qua
            ],
        }


@router.delete("/sections/{section_code}/packages/{package_version_id}")
def go_bo_goi(
    section_code: str,
    package_version_id: int,
    request: Request,
):
    """Go lien ket goi SCORM khoi lop hoc phan."""
    person_code = lay_person_code(request)
    kiem_tra_giang_vien(section_code, person_code)

    with phien_lam_viec() as s:
        lien_ket = s.get(
            SectionPackage,
            (section_code, package_version_id),
        )

        if lien_ket is None:
            raise HTTPException(
                status_code=404,
                detail="Goi SCORM chua duoc gan vao lop",
            )

        s.delete(lien_ket)

    return {
        "message": "Go goi SCORM khoi lop thanh cong",
        "section_code": section_code,
        "package_version_id": package_version_id,
    }



@router.post(
    "/sections/{section_code}/packages/{package_version_id}/attempts"
)
def tao_hoac_tiep_tuc_attempt(
    section_code: str,
    package_version_id: int,
    request: Request,
):
    """Tao Attempt moi hoac tiep tuc Attempt dang hoc."""
    person_code = lay_person_code(request)

    with phien_lam_viec() as s:
        # 1. Kiem tra lop hoc phan.
        section = s.get(Section, section_code)
        if section is None:
            raise HTTPException(
                status_code=404,
                detail="Khong tim thay lop hoc phan",
            )

        # 2. Kiem tra nguoi hoc da dang ky lop.
        enrollment = s.get(
            Enrollment,
            (section_code, person_code),
        )

        if enrollment is None or enrollment.status != "registered":
            raise HTTPException(
                status_code=403,
                detail="Ban khong co quyen hoc lop hoc phan nay",
            )

        person = s.get(Person, person_code)

        if (
            person is None
            or person.person_type != "student"
            or enrollment.role != "student"
        ):
            raise HTTPException(
                status_code=403,
                detail="Chi nguoi hoc moi co quyen tao Attempt",
            )

        # 3. Kiem tra goi da duoc gan vao lop.
        section_package = s.get(
            SectionPackage,
            (section_code, package_version_id),
        )
        if section_package is None:
            raise HTTPException(
                status_code=403,
                detail="Goi SCORM chua duoc gan vao lop hoc phan",
            )

        # 4. Kiem tra phien ban goi.
        package_version = s.get(
            PackageVersion,
            package_version_id,
        )
        if package_version is None:
            raise HTTPException(
                status_code=404,
                detail="Khong tim thay goi SCORM",
            )

        if package_version.status != "ready":
            raise HTTPException(
                status_code=409,
                detail="Phien ban goi SCORM chua san sang",
            )

        # 5. Lay danh sach SCO cua phien ban goi.
        scos = s.scalars(
            select(Sco)
            .where(Sco.package_version_id == package_version_id)
            .order_by(Sco.position)
        ).all()

        if not scos:
            raise HTTPException(
                status_code=409,
                detail="Goi SCORM chua co SCO",
            )
        sco_theo_id = {sco.id: sco for sco in scos}

        # 6. Tim Attempt gan nhat cua nguoi hoc.
        attempt_cu = s.scalar(
            select(Attempt)
            .where(
                Attempt.section_code == section_code,
                Attempt.person_code == person_code,
                Attempt.package_version_id == package_version_id,
            )
            .order_by(Attempt.attempt_number.desc())
            .limit(1)
        )

        # 7. Neu dang hoc thi tiep tuc Attempt cu.
        if attempt_cu is not None:
            if attempt_cu.status == "in_progress":
                states = s.scalars(
                    select(AttemptScoState)
                    .where(
                        AttemptScoState.attempt_id == attempt_cu.id
                    )
                ).all()

                return {
                    "attempt_id": attempt_cu.id,
                    "attempt_number": attempt_cu.attempt_number,
                    "status": attempt_cu.status,
                    "resumed": True,
                    "sco_states": [
                        {
                            "sco_id": state.sco_id,
                            "cmi_data": state.cmi_data,
                            "launch_url": (
                                f"/content/attempts/{attempt_cu.id}"
                                f"/scos/{state.sco_id}/"
                                f"{quote(sco_theo_id[state.sco_id].href, safe='/')}"
                            ),
                        }
                        for state in states
                    ],
                }

            if attempt_cu.status not in {
                "completed",
                "passed",
                "failed",
            }:
                raise HTTPException(
                    status_code=409,
                    detail="Trang thai Attempt khong hop le",
                )

            attempt_number = attempt_cu.attempt_number + 1
        else:
            attempt_number = 1

        # 8. Tao Attempt moi.
        attempt_moi = Attempt(
            section_code=section_code,
            person_code=person_code,
            package_version_id=package_version_id,
            attempt_number=attempt_number,
            status="in_progress",
        )

        s.add(attempt_moi)
        s.flush()

        # 9. Khoi tao CMI rieng cho tung SCO.
        states_moi = []
        for sco in scos:
            state = AttemptScoState(
                attempt_id=attempt_moi.id,
                sco_id=sco.id,
                cmi_data=tao_cmi_mac_dinh(package_version.scorm_version),
            )
            s.add(state)
            states_moi.append(state)

        s.flush()

        return {
            "attempt_id": attempt_moi.id,
            "attempt_number": attempt_moi.attempt_number,
            "status": attempt_moi.status,
            "resumed": False,
            "sco_states": [
                {
                    "sco_id": state.sco_id,
                    "cmi_data": state.cmi_data,
                    "launch_url": (
                        f"/content/attempts/{attempt_moi.id}"
                        f"/scos/{state.sco_id}/"
                        f"{quote(sco_theo_id[state.sco_id].href, safe='/')}"
                    ),
                }
                for state in states_moi
            ],
        }
