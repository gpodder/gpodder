
import Qt 4.7
import com.nokia.meego 1.0

import 'config.js' as Config

PageStackWindow {
    id: rootWindow
    property variant main: mainObject
    property bool fullsize: (platformWindow.viewMode == WindowState.Fullsize)

    // Unused boolean activity variables:
    //  - platformWindow.visible - Visible somewhere
    //  - platformWindow.active - Active (input focus?)

    showToolBar: mainObject.canGoBack || mainObject.hasPlayButton || mainObject.hasSearchButton

    // Hide status bar in landscape mode
    showStatusBar: screen.currentOrientation == Screen.Portrait

    initialPage: Page {
        id: mainPage
        //orientationLock: PageOrientation.LockPortrait

        tools: ToolBarLayout {
            ToolIcon {
                id: toolBack
                anchors.left: parent.left
                iconId: "icon-m-toolbar-back-white"
                onClicked: mainObject.goBack()
                visible: mainObject.canGoBack
            }

            ToolIcon {
                id: toolMyGpo
                onClicked: mainObject.openMyGpo()
                anchors.left: parent.left
                iconId: "toolbar-view-menu"
                visible: !toolBack.visible && mainObject.state == 'podcasts' && !mainObject.myGpoSheetVisible
            }

            ToolIcon {
                id: toolAdd
                iconId: "icon-m-toolbar-add-white"
                onClicked: mainObject.clickSearchButton()
                visible: mainObject.hasSearchButton
                anchors.right: toolPlay.visible?toolPlay.left:toolPlay.right
            }

            ToolIcon {
                id: toolPlay
                iconId: "icon-m-toolbar-content-audio-white"
                onClicked: mainObject.clickPlayButton()
                visible: mainObject.hasPlayButton
                anchors.right: parent.right
            }
        }

        Main {
            id: mainObject
            anchors.fill: parent
        }
    }

    Component.onCompleted: {
        theme.inverted = true
    }
}

