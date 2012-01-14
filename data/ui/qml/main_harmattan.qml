
import Qt 4.7
import com.nokia.meego 1.0

import 'config.js' as Config

PageStackWindow {
    id: rootWindow
    property variant main: mainObject
    property bool fullsize: (platformWindow.viewMode == WindowState.Fullsize)

    function _(x) {
        return controller.translate(x)
    }

    // Unused boolean activity variables:
    //  - platformWindow.visible - Visible somewhere
    //  - platformWindow.active - Active (input focus?)

    showToolBar: (mainObject.canGoBack || mainObject.hasPlayButton || mainObject.hasSearchButton) && !aboutBox.opacity

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
                id: toolMenu
                onClicked: {
                    /*if (mainObject.currentPodcast !== undefined) {
                        controller.podcastContextMenu(mainObject.currentPodcast)
                    } else {*/
                        hrmtnMainViewMenu.open()
                    //}
                }
                anchors.right: parent.right
                iconId: "toolbar-view-menu"
                visible: (!toolBack.visible && mainObject.state == 'podcasts' && !mainObject.myGpoSheetVisible) //|| (mainObject.currentPodcast !== undefined && mainObject.state == 'episodes')
            }

            ToolIcon {
                id: toolRefresh
                iconId: 'icon-m-toolbar-refresh-white'
                onClicked: controller.updateAllPodcasts()
                visible: mainObject.hasSearchButton && mainObject.hasPodcasts
                anchors.left: parent.left
            }

            ToolIcon {
                id: toolAdd
                iconId: "icon-m-toolbar-add-white"
                onClicked: mainObject.clickSearchButton()
                visible: mainObject.hasSearchButton
                anchors.centerIn: parent
                //anchors.right: toolPlay.visible?toolPlay.left:toolPlay.right
            }

            ToolButton {
                id: toolFilter
                visible: mainObject.hasFilterButton
                onClicked: mainObject.showFilterDialog()
                anchors.centerIn: parent

                Label {
                    color: 'white'
                    text: mainObject.currentFilterText
                    anchors.centerIn: parent
                }
            }

            ToolIcon {
                id: toolPlay
                iconId: "icon-m-toolbar-content-audio-white"
                onClicked: mainObject.clickPlayButton()
                visible: mainObject.hasPlayButton && !toolMenu.visible
                anchors.right: parent.right
            }
        }

        ContextMenu {
            id: hrmtnMainViewMenu

            MenuLayout {
                MenuItem {
                    text: _('gpodder.net settings')
                    onClicked: {
                        hrmtnMainViewMenu.close()
                        mainObject.openMyGpo()
                    }
                }
                MenuItem {
                    text: _('Now playing')
                    onClicked: {
                        hrmtnMainViewMenu.close()
                        mainObject.clickPlayButton()
                    }
                    visible: mainObject.hasPlayButton
                }
                MenuItem {
                    text: _('About gPodder')
                    onClicked: {
                        hrmtnMainViewMenu.close()
                        aboutBox.opacity = 1
                    }
                }
            }
        }

        Main {
            id: mainObject
            anchors.fill: parent
        }
        Rectangle {
            id: aboutBox
            anchors.fill: parent
            color: '#dd000000'

            opacity: 0
            Behavior on opacity { PropertyAnimation { } }

            Column {
                anchors.centerIn: parent
                spacing: 5
                scale: Math.pow(parent.opacity, 3)

                Item {
                    height: aboutBoxIcon.sourceSize.height
                    width: parent.width

                    Image {
                        id: aboutBoxIcon
                        anchors.centerIn: parent
                        source: 'artwork/gpodder200.png'
                    }
                }

                Text {
                    color: 'white'
                    font.pixelSize: 30
                    font.bold: true
                    text: 'gPodder ' + controller.getVersion()
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                }

                Text {
                    color: 'white'
                    text: controller.getURL()
                    font.pixelSize: 25
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                }

                Text {
                    color: 'white'
                    font.pixelSize: 17
                    text: '\n' + controller.getCopyright() + '\n' + controller.getLicense()
                    wrapMode: Text.WordWrap
                    width: mainObject.width * .95
                    horizontalAlignment: Text.AlignHCenter
                }
            }

            MouseArea {
                anchors.fill: parent
                onClicked: {
                    if (parent.opacity > 0) {
                        parent.opacity = 0
                    } else {
                        parent.opacity = 1
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        theme.inverted = true
    }
}

