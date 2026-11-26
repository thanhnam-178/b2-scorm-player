
(function (global) {
    "use strict";

    const SCORM_12 = "1.2";
    const SCORM_2004 = "2004";

    const ERROR = {
        "1.2": {
            NO_ERROR: "0",
            GENERAL: "101",
            INVALID_ARGUMENT: "201",
            NOT_INITIALIZED: "301",
            ALREADY_INITIALIZED: "101",
            TERMINATED: "101",
            READ_ONLY: "403",
            WRITE_ONLY: "404",
            NOT_IMPLEMENTED: "401",
            INVALID_SET_VALUE: "405",
        },
        "2004": {
            NO_ERROR: "0",
            GENERAL: "101",
            INVALID_ARGUMENT: "201",
            NOT_INITIALIZED: "122",
            ALREADY_INITIALIZED: "103",
            TERMINATED: "113",
            READ_ONLY: "404",
            WRITE_ONLY: "405",
            NOT_IMPLEMENTED: "401",
            INVALID_SET_VALUE: "406",
        },
    };

    const DEFAULTS = {
        "1.2": {
            "cmi.core.lesson_status": "not attempted",
            "cmi.core.score.raw": "",
            "cmi.core.score.min": "",
            "cmi.core.score.max": "",
        },
        "2004": {
            "cmi.completion_status": "not attempted",
            "cmi.success_status": "unknown",
            "cmi.score.raw": "",
            "cmi.score.min": "",
            "cmi.score.max": "",
            "cmi.score.scaled": "",
        },
    };

    function taoAdapter(config) {
        const attemptId = Number(config.attemptId);
        const scoId = Number(config.scoId);
        const version = String(config.scormVersion);

        if (
            !Number.isInteger(attemptId) ||
            !Number.isInteger(scoId) ||
            !DEFAULTS[version]
        ) {
            throw new Error("Cau hinh SCORM Adapter khong hop le");
        }

        const baseUrl =
            `/api/v1/attempts/${attemptId}/scos/${scoId}`;

        let cmiData = {};
        let initialized = false;
        let terminated = false;
        let lastError = ERROR[version].NO_ERROR;
        let diagnostic = "No error";
        let dirty = false;

        const error = ERROR[version];

        function setError(code, message) {
            lastError = code;
            diagnostic = message;
            return "false";
        }

        function clearError() {
            lastError = error.NO_ERROR;
            diagnostic = "No error";
        }

        function request(method, path, body) {
            const xhr = new XMLHttpRequest();

            try {
                xhr.open(method, baseUrl + path, false);
                xhr.withCredentials = true;

                if (body !== undefined) {
                    xhr.setRequestHeader(
                        "Content-Type",
                        "application/json"
                    );
                }

                xhr.send(
                    body === undefined
                        ? null
                        : JSON.stringify(body)
                );

                if (xhr.status < 200 || xhr.status >= 300) {
                    return {
                        ok: false,
                        status: xhr.status,
                        data: null,
                    };
                }

                return {
                    ok: true,
                    status: xhr.status,
                    data: xhr.responseText
                        ? JSON.parse(xhr.responseText)
                        : {},
                };
            } catch (exception) {
                return {
                    ok: false,
                    status: 0,
                    data: null,
                };
            }
        }

        function mergeDefaults(data) {
            return {
                ...DEFAULTS[version],
                ...(data || {}),
            };
        }

        function taoDuLieuCMIGuiBackend() {
            const data = { ...cmiData };

            for (const element of Object.keys(data)) {
                const laTruongDiem =
                    element.endsWith(".score.raw") ||
                    element.endsWith(".score.min") ||
                    element.endsWith(".score.max") ||
                    element === "cmi.score.scaled";

                if (laTruongDiem && data[element] === "") {
                    delete data[element];
                }
            }

            return data;
        }

        function initialize(argument) {
            if (argument !== "") {
                return setError(
                    error.INVALID_ARGUMENT,
                    "Initialize chi chap nhan chuoi rong"
                );
            }

            if (initialized) {
                return setError(
                    error.ALREADY_INITIALIZED,
                    "Runtime da Initialize"
                );
            }

            if (terminated) {
                return setError(
                    error.TERMINATED,
                    "Runtime da Terminate"
                );
            }

            const result = request("POST", "/initialize");

            if (!result.ok) {
                return setError(
                    error.GENERAL,
                    "Khong the Initialize Runtime"
                );
            }

            cmiData = mergeDefaults(result.data.cmi_data);
            initialized = true;
            dirty = false;
            clearError();

            return "true";
        }

        function getValue(element) {
            if (!initialized || terminated) {
                setError(
                    error.NOT_INITIALIZED,
                    "Runtime chua Initialize hoac da Terminate"
                );
                return "";
            }

            if (typeof element !== "string" || !element) {
                setError(
                    error.INVALID_ARGUMENT,
                    "Ten CMI khong hop le"
                );
                return "";
            }

            if (Object.prototype.hasOwnProperty.call(cmiData, element)) {
                clearError();
                return String(cmiData[element]);
            }

            setError(
                error.NOT_IMPLEMENTED,
                "Truong CMI chua duoc Adapter ho tro"
            );

            return "";
        }

        function setValue(element, value) {
            if (!initialized || terminated) {
                return setError(
                    error.NOT_INITIALIZED,
                    "Runtime chua Initialize hoac da Terminate"
                );
            }

            if (
                typeof element !== "string" ||
                typeof value !== "string"
            ) {
                return setError(
                    error.INVALID_ARGUMENT,
                    "Tham so SetValue khong hop le"
                );
            }

            if (!Object.prototype.hasOwnProperty.call(cmiData, element)) {
                return setError(
                    error.NOT_IMPLEMENTED,
                    "Truong CMI chua duoc Adapter ho tro"
                );
            }

            if (element === "cmi.core.lesson_status") {
                const allowed = [
                    "passed",
                    "completed",
                    "failed",
                    "incomplete",
                    "browsed",
                    "not attempted",
                ];

                if (!allowed.includes(value)) {
                    return setError(
                        error.INVALID_SET_VALUE,
                        "Gia tri lesson_status khong hop le"
                    );
                }
            }

            if (element === "cmi.completion_status") {
                const allowed = [
                    "completed",
                    "incomplete",
                    "not attempted",
                    "unknown",
                ];

                if (!allowed.includes(value)) {
                    return setError(
                        error.INVALID_SET_VALUE,
                        "Gia tri completion_status khong hop le"
                    );
                }
            }

            if (element === "cmi.success_status") {
                const allowed = ["passed", "failed", "unknown"];

                if (!allowed.includes(value)) {
                    return setError(
                        error.INVALID_SET_VALUE,
                        "Gia tri success_status khong hop le"
                    );
                }
            }

            if (
                element.endsWith(".score.raw") ||
                element.endsWith(".score.min") ||
                element.endsWith(".score.max")
            ) {
                if (value !== "" && !Number.isFinite(Number(value))) {
                    return setError(
                        error.INVALID_SET_VALUE,
                        "Diem phai la mot so hop le"
                    );
                }
            }

            if (element === "cmi.score.scaled") {
                const number = Number(value);

                if (
                    value === "" ||
                    !Number.isFinite(number) ||
                    number < -1 ||
                    number > 1
                ) {
                    return setError(
                        error.INVALID_SET_VALUE,
                        "score.scaled phai nam trong [-1, 1]"
                    );
                }
            }

            cmiData[element] = value;
            dirty = true;
            clearError();

            return "true";
        }

        function commit(argument) {
            if (argument !== "") {
                return setError(
                    error.INVALID_ARGUMENT,
                    "Commit chi chap nhan chuoi rong"
                );
            }

            if (!initialized || terminated) {
                return setError(
                    error.NOT_INITIALIZED,
                    "Runtime chua Initialize hoac da Terminate"
                );
            }

            if (!dirty) {
                clearError();
                return "true";
            }

            const result = request("PUT", "/cmi", {
                cmi_data: taoDuLieuCMIGuiBackend(),
            });

            if (!result.ok) {
                return setError(
                    error.GENERAL,
                    "Backend tu choi Commit CMI"
                );
            }

            cmiData = mergeDefaults(result.data.cmi_data);
            dirty = false;
            clearError();

            return "true";
        }

        function terminate(argument) {
            if (argument !== "") {
                return setError(
                    error.INVALID_ARGUMENT,
                    "Terminate chi chap nhan chuoi rong"
                );
            }

            if (!initialized || terminated) {
                return setError(
                    error.NOT_INITIALIZED,
                    "Runtime chua Initialize hoac da Terminate"
                );
            }

            const result = request("POST", "/terminate", {
                cmi_data: taoDuLieuCMIGuiBackend(),
            });

            if (!result.ok) {
                return setError(
                    error.GENERAL,
                    "Backend tu choi Terminate"
                );
            }

            terminated = true;
            dirty = false;
            clearError();

            return "true";
        }

        function getLastError() {
            return lastError;
        }

        function getErrorString(code) {
            const messages = {
                "0": "No error",
                "101": "General exception",
                "103": "Already initialized",
                "113": "Terminate after termination",
                "122": "Not initialized",
                "201": "Invalid argument",
                "301": "Not initialized",
                "401": "Not implemented",
                "403": "Read only element",
                "404": "Write only element",
                "405": "Incorrect data type or invalid value",
                "406": "Data model element value out of range",
            };

            return messages[String(code)] || "Unknown error";
        }

        function getDiagnostic() {
            return diagnostic;
        }

        return {
            // SCORM 2004
            Initialize: initialize,
            GetValue: getValue,
            SetValue: setValue,
            Commit: commit,
            Terminate: terminate,
            GetLastError: getLastError,
            GetErrorString: getErrorString,
            GetDiagnostic: getDiagnostic,

            // SCORM 1.2
            LMSInitialize: initialize,
            LMSGetValue: getValue,
            LMSSetValue: setValue,
            LMSCommit: commit,
            LMSFinish: terminate,
            LMSGetLastError: getLastError,
            LMSGetErrorString: getErrorString,
            LMSGetDiagnostic: getDiagnostic,
        };
    }

    global.createScormAdapter = taoAdapter;
})(window);
