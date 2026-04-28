import subprocess
import psutil
import os
import ctypes
from ctypes import wintypes


class CommandExecutor:
    def __init__(self):
        self.process = None
        self._job_handle = None

    def execute_command(self, run_cmd, stdout=None):
        if self.process and self.process.poll() is None:
            print("The command is already running. Please wait for it to finish.")
        else:
            if self._job_handle is not None and os.name == "nt":
                try:
                    ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(self._job_handle))
                except Exception:
                    pass
                finally:
                    self._job_handle = None

            creationflags = 0
            if os.name == "nt":
                creationflags |= subprocess.CREATE_NEW_PROCESS_GROUP

            use_shell = isinstance(run_cmd, str)
            self.process = subprocess.Popen(
                run_cmd,
                stdout=stdout,
                shell=use_shell,
                creationflags=creationflags,
            )
            self._assign_to_job_object_if_supported()

    def kill_command(self):
        if self._job_handle is not None and os.name == "nt":
            try:
                ctypes.windll.kernel32.CloseHandle(wintypes.HANDLE(self._job_handle))
            except Exception as e:
                print(f"Error when terminating job object: {e}")
            finally:
                self._job_handle = None
                self.process = None
            print("The running process has been terminated.")
            return

        if self.process and self.process.poll() is None:
            try:
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
                print("The running process has been terminated.")
            except psutil.NoSuchProcess:
                print("The process does not exist.")
            except Exception as e:
                print(f"Error when terminating process: {e}")
        else:
            print("There is no running process to kill.")

    def _assign_to_job_object_if_supported(self):
        if os.name != "nt" or self.process is None:
            return
        try:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            CreateJobObjectW = kernel32.CreateJobObjectW
            CreateJobObjectW.argtypes = [wintypes.LPVOID, wintypes.LPCWSTR]
            CreateJobObjectW.restype = wintypes.HANDLE

            SetInformationJobObject = kernel32.SetInformationJobObject
            SetInformationJobObject.argtypes = [wintypes.HANDLE, wintypes.INT, wintypes.LPVOID, wintypes.DWORD]
            SetInformationJobObject.restype = wintypes.BOOL

            AssignProcessToJobObject = kernel32.AssignProcessToJobObject
            AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
            AssignProcessToJobObject.restype = wintypes.BOOL

            CloseHandle = kernel32.CloseHandle
            CloseHandle.argtypes = [wintypes.HANDLE]
            CloseHandle.restype = wintypes.BOOL

            JobObjectExtendedLimitInformation = 9
            JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
            LARGE_INTEGER = ctypes.c_longlong
            ULARGE_INTEGER = ctypes.c_ulonglong

            class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("PerProcessUserTimeLimit", LARGE_INTEGER),
                    ("PerJobUserTimeLimit", LARGE_INTEGER),
                    ("LimitFlags", wintypes.DWORD),
                    ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t),
                    ("ActiveProcessLimit", wintypes.DWORD),
                    ("Affinity", ctypes.c_size_t),
                    ("PriorityClass", wintypes.DWORD),
                    ("SchedulingClass", wintypes.DWORD),
                ]

            class IO_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("ReadOperationCount", ULARGE_INTEGER),
                    ("WriteOperationCount", ULARGE_INTEGER),
                    ("OtherOperationCount", ULARGE_INTEGER),
                    ("ReadTransferCount", ULARGE_INTEGER),
                    ("WriteTransferCount", ULARGE_INTEGER),
                    ("OtherTransferCount", ULARGE_INTEGER),
                ]

            class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(ctypes.Structure):
                _fields_ = [
                    ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
                    ("IoInfo", IO_COUNTERS),
                    ("ProcessMemoryLimit", ctypes.c_size_t),
                    ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t),
                    ("PeakJobMemoryUsed", ctypes.c_size_t),
                ]

            job_handle = CreateJobObjectW(None, None)
            if not job_handle:
                return

            info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
            info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE

            ok = SetInformationJobObject(
                job_handle,
                JobObjectExtendedLimitInformation,
                ctypes.byref(info),
                ctypes.sizeof(info),
            )
            if not ok:
                CloseHandle(job_handle)
                return

            proc_handle = wintypes.HANDLE(int(self.process._handle))
            ok = AssignProcessToJobObject(job_handle, proc_handle)
            if not ok:
                CloseHandle(job_handle)
                return

            self._job_handle = int(job_handle)
        except Exception:
            self._job_handle = None
