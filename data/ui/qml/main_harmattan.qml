
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

    showToolBar: !switcherDisplay.visible && (mainObject.canGoBack || mainObject.hasPlayButton || mainObject.hasSearchButton)

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

        Item {
            id: switcherDisplay

            anchors.fill: parent
            visible: !rootWindow.fullsize && mainObject.playing

            Rectangle {
                color: '#dd000000'
                anchors.fill: parent
            }

            Column {
                anchors {
                    left: parent.left
                    bottom: parent.bottom
                    leftMargin: switcherDisplay.width * .05
                }

                Label {
                    font.pixelSize: 30
                    text: 'gPodder - ' + _('Now playing')
                    color: '#aaa'
                }

                Item {
                    width: 1
                    height: Config.largeSpacing
                }

                Label {
                    font.pixelSize: 40
                    color: 'white'
                    text: (mainObject.currentEpisode!=undefined)?mainObject.currentEpisode.qtitle:''
                }

                Label {
                    font.pixelSize: 55
                    font.bold: true
                    color: '#ccc'
                    text: (mainObject.currentEpisode!=undefined)?mainObject.currentEpisode.qpositiontext:''
                }

                Item {
                    width: 1
                    height: parent.anchors.leftMargin
                }
            }
        }
    }

    Component.onCompleted: {
        theme.inverted = true
    }
}

