
import com.nokia.meego 1.0

PageStackWindow {
    property bool fullsize: (platformWindow.viewMode == WindowState.Fullsize)

    // Unused boolean activity variables:
    //  - platformWindow.visible - Visible somewhere
    //  - platformWindow.active - Active (input focus?)

    // Hide status bar in landscape mode
    showStatusBar: screen.currentOrientation == Screen.Portrait
}

