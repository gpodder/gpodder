
#include <stdio.h>
#include <wininet.h>
#include <commctrl.h>

unsigned long
DownloadFile(const char *filename, const char *url, unsigned long size)
{
    HINTERNET inet;
    HINTERNET connection;
    FILE *out;
    char buf[1024*10];
    char line[1024];
    long readBytes;
    unsigned long totalBytes = 0;
    int error = 0;
    HWND dlg;
    HWND progress;
    HWND label;
    MSG msg;

#if defined(GPODDER_GUI)
    dlg = CreateDialog(NULL, "PROGRESS", NULL, NULL);

    progress = GetDlgItem(dlg, 1);
    SendMessage(progress, PBM_SETRANGE, 0, MAKELPARAM(0, 100));

    label = GetDlgItem(dlg, 3);
    SendMessage(label, WM_SETTEXT, 0, (LPARAM)filename);

    label = GetDlgItem(dlg, 4);
#endif

    inet = InternetOpen("gpodder-dependency-downloader",
            INTERNET_OPEN_TYPE_PRECONFIG,
            NULL,
            NULL,
            0);

    connection = InternetOpenUrl(inet,
            url,
            NULL,
            0,
            INTERNET_FLAG_NO_AUTH | INTERNET_FLAG_NO_CACHE_WRITE |
            INTERNET_FLAG_NO_COOKIES | INTERNET_FLAG_NO_UI,
            0);

    out = fopen(filename, "wb");
    if (out == NULL) {
        error = 1;
    }

    while (out != NULL) {
        if (!InternetReadFile(connection,
                    buf,
                    sizeof(buf),
                    &readBytes)) {
            error = 1;
            break;
        }

        if (readBytes == 0) {
            break;
        }

        fwrite(buf, readBytes, 1, out);

        totalBytes += readBytes;

        snprintf(line, sizeof(line), "%.2f / %.2f MB",
                (float)totalBytes / (float)(1024*1024),
                (float)size / (float)(1024*1024));

#if defined(GPODDER_CLI)
        fprintf(stderr, "Downloading: %s\r", line);
#endif

#if defined(GPODDER_GUI)
        SendMessage(label, WM_SETTEXT,
                0, (LPARAM)TEXT(line));

        SendMessage(progress, PBM_SETPOS,
                (int)(100*(float)totalBytes/(float)size), 0);

        while (PeekMessage(&msg, dlg, 0, 0, PM_NOREMOVE)) {
            if (GetMessage(&msg, NULL, 0, 0) > 0) {
                TranslateMessage(&msg);
                DispatchMessage(&msg);
            }
        }
#endif
    }

#if defined(GPODDER_GUI)
    DestroyWindow(dlg);
#endif

    fclose(out);
    InternetCloseHandle(connection);
    InternetCloseHandle(inet);
    if (error) {
        return 0;
    } else {
        return totalBytes;
    }
}

