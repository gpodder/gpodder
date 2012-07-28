
import Qt 4.7
import com.nokia.meego 1.0
import QtWebKit 1.0

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

    showToolBar: (mainObject.canGoBack || mainObject.hasPlayButton || mainObject.hasSearchButton) && (mainObject.hasPodcasts || mainObject.canGoBack) || pageStack.depth > 1

    // Hide status bar in landscape mode
    showStatusBar: screen.currentOrientation == Screen.Portrait

    initialPage: Page {
        id: mainPage
        orientationLock: {
            if (configProxy.autorotate) {
                PageOrientation.Automatic
            } else {
                PageOrientation.LockPortrait
            }
        }

        tools: ToolBarLayout {
            ToolIcon {
                id: toolBack
                anchors.left: parent.left
                iconId: "icon-m-toolbar-back-white"
                onClicked: mainObject.goBack()
                visible: mainObject.canGoBack
            }

            ToolIcon {
                id: toolFlattr
                iconSource: 'artwork/flattr.png'
                visible: mainObject.state == 'shownotes'

                opacity: (mainObject.state == 'shownotes') && (labelFlattr.text !== '')
                Behavior on opacity { PropertyAnimation { } }

                anchors.right: toolPlay.visible?toolPlay.left:parent.right
                onClicked: {
                    controller.flattrEpisode(mainObject.showNotesEpisode);
                }
            }

            Connections {
                target: mainObject
                onShowNotesEpisodeChanged: {
                    controller.updateFlattrButtonText(mainObject.showNotesEpisode);
                }
            }

            Label {
                id: labelFlattr
                color: 'white'
                anchors.right: toolFlattr.left
                anchors.verticalCenter: toolFlattr.verticalCenter
                opacity: toolFlattr.opacity
                visible: toolFlattr.visible

                text: controller.flattrButtonText
            }

            ToolIcon {
                id: toolMenu
                onClicked: {
                    if (mainObject.state === 'episodes') {
                        hrmtnEpisodesMenu.open();
                    } else {
                        hrmtnMainViewMenu.open();
                    }
                }
                anchors.right: parent.right
                iconId: "toolbar-view-menu"
                visible: (!toolBack.visible && mainObject.state == 'podcasts') || (mainObject.currentPodcast !== undefined && mainObject.state == 'episodes')
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
                width: 300
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
                    text: _('Now playing')
                    onClicked: nowPlayingMenuItem.clicked()
                }
                MenuItem {
                    text: _('Settings')
                    onClicked: {
                        hrmtnMainViewMenu.close()
                        settingsPage.loadSettings()
                        pageStack.push(settingsPage)
                    }
                }
                MenuItem {
                    text: _('About gPodder')
                    onClicked: {
                        hrmtnMainViewMenu.close()
                        pageStack.push(aboutBox)
                    }
                }
            }
        }

        ContextMenu {
            id: hrmtnEpisodesMenu

            MenuLayout {
                MenuItem {
                    id: nowPlayingMenuItem
                    text: _('Now playing')
                    onClicked: {
                        if (mainObject.hasPlayButton) {
                            hrmtnMainViewMenu.close();
                            mainObject.clickPlayButton();
                        } else {
                            mainObject.showMessage(_('Playlist empty'));
                        }
                    }
                }
                MenuItem {
                    text: _('Download episodes')
                    onClicked: {
                        mainObject.showMultiEpisodesSheet(text, _('Download'), 'download');
                        hrmtnMainViewMenu.close()
                    }
                }
                MenuItem {
                    text: _('Playback episodes')
                    onClicked: {
                        mainObject.showMultiEpisodesSheet(text, _('Play'), 'play');
                        hrmtnMainViewMenu.close()
                    }
                }
                MenuItem {
                    text: _('Delete episodes')
                    onClicked: {
                        mainObject.showMultiEpisodesSheet(text, _('Delete'), 'delete');
                        hrmtnMainViewMenu.close()
                    }
                }
            }
        }

        Main {
            id: mainObject
            anchors.fill: parent
        }
    }

    Page {
        id: aboutBox
        property color textColor: 'white'
        orientationLock: PageOrientation.LockPortrait

        tools: ToolBarLayout {
            ToolIcon {
                anchors.left: parent.left
                iconId: "icon-m-toolbar-back-white"
                onClicked: {
                    pageStack.pop()
                }
            }
        }

        Flickable {
            id: aboutFlickable
            anchors.fill: parent
            anchors.margins: Config.largeSpacing
            contentWidth: aboutColumn.width
            contentHeight: aboutColumn.height
            flickableDirection: Flickable.VerticalFlick

            Column {
                id: aboutColumn
                spacing: 5
                width: 440

                Item {
                    height: aboutBoxIcon.sourceSize.height + 50
                    width: parent.width

                    Image {
                        id: aboutBoxIcon
                        anchors {
                            horizontalCenter: parent.horizontalCenter
                            bottom: parent.bottom
                        }
                        source: 'artwork/gpodder200.png'
                    }
                }

                Text {
                    color: aboutBox.textColor
                    font.pixelSize: 30
                    font.bold: true
                    text: 'gPodder'
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                }

                SettingsHeader {
                    text: _('About')
                }

                Text {
                    color: aboutBox.textColor
                    font.pixelSize: 21
                    font.bold: true
                    text: 'Version ' + controller.getVersion() + ' (' + controller.getReleased() + ')'
                }

                Text {
                    color: aboutBox.textColor
                    text: controller.getURL()
                    font.pixelSize: 19
                }

                Text {
                    color: aboutBox.textColor
                    font.pixelSize: 17
                    text: '\n' + controller.getCopyright() + '\n' + controller.getLicense()
                    wrapMode: Text.WordWrap
                    width: parent.width
                }

                SettingsHeader {
                    text: _('Thanks')
                }

                Text {
                    color: aboutBox.textColor
                    font.pixelSize: 19
                    text: 'Andrew Zhilin (Design / zhil.in)\nMatti Airas (MeeGo Team / Harmattan Python)\nPauli Rinne (Etnoteam Finland)\nPySide Team (INdT / OpenBossa)\nQuim Gil (Nokia)\nRonan Mac Laverty (Nokia Developer)'
                }

                SettingsHeader {
                    text: _('Credits')
                }

                Text {
                    color: aboutBox.textColor
                    font.pixelSize: 19
                    text: controller.getCredits()
                }
            }
        }

        ScrollDecorator {
            flickableItem: aboutFlickable
        }
    }

    Page {
        id: flattrLoginPage
        orientationLock: mainPage.orientationLock

        tools: ToolBarLayout {
            ToolIcon {
                id: flattrLoginPageClose
                anchors.left: parent.left
                iconId: "icon-m-toolbar-back-white"
                onClicked: {
                    pageStack.pop()
                }
            }
        }

        WebView {
            id: flattrLoginWebView
            anchors.fill: parent
            preferredWidth: width
            preferredHeight: height
            onLoadFinished: {
                var url_str = '' + url;
                if (url_str.indexOf(controller.getFlattrCallbackURL()) == 0) {
                    controller.processFlattrCode(url);
                    pageStack.pop();
                }
            }
        }
    }


    Page {
        id: settingsPage
        orientationLock: mainPage.orientationLock

        function loadSettings() {
            settingsAutorotate.checked = configProxy.autorotate
            settingsIndexing.checked = trackerMinerConfig.get_index_podcasts()

            flattrOnPlaySwitch.checked = configProxy.flattrOnPlay

            myGpoEnableSwitch.checked = controller.myGpoEnabled
            myGpoUsernameField.text = controller.myGpoUsername
            myGpoPasswordField.text = controller.myGpoPassword
            myGpoDeviceCaptionField.text = controller.myGpoDeviceCaption
        }

        tools: ToolBarLayout {
            ToolIcon {
                id: settingsPageClose
                anchors.left: parent.left
                iconId: "icon-m-toolbar-back-white"
                onClicked: {
                    controller.myGpoUsername = myGpoUsernameField.text
                    controller.myGpoPassword = myGpoPasswordField.text
                    controller.myGpoDeviceCaption = myGpoDeviceCaptionField.text
                    controller.myGpoEnabled = myGpoEnableSwitch.checked && (controller.myGpoUsername != '' && controller.myGpoPassword != '')
                    controller.saveMyGpoSettings()

                    pageStack.pop()
                }
            }
        }


        Item {
            id: myGpoSheetContent
            anchors.fill: parent

            Flickable {
                anchors.fill: parent
                anchors.margins: Config.largeSpacing
                contentWidth: myGpoSettingsColumn.width
                contentHeight: myGpoSettingsColumn.height

                Column {
                    id: myGpoSettingsColumn
                    width: myGpoSheetContent.width - Config.largeSpacing * 2
                    spacing: 4

                    Label {
                        text: _('gPodder settings')
                        font.pixelSize: 30
                    }

                    SettingsHeader { text: _('Screen orientation') }

                    SettingsSwitch {
                        id: settingsAutorotate
                        text: _('Automatic rotation')
                        onCheckedChanged: {
                            configProxy.autorotate = checked
                        }
                    }

                    SettingsHeader { text: _('Media indexing') }

                    SettingsSwitch {
                        id: settingsIndexing
                        text: _('Show podcasts in Music app')
                        onCheckedChanged: {
                            trackerMinerConfig.set_index_podcasts(checked)
                        }
                    }

                    SettingsHeader { text: 'Flattr' }

                    Button {
                        text: {
                            if (configProxy.flattrToken !== '') {
                                _('Sign out')
                            } else {
                                _('Sign in to Flattr')
                            }
                        }
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width * .8
                        onClicked: {
                            if (configProxy.flattrToken !== '') {
                                /* Logout */
                                configProxy.flattrToken = '';
                            } else {
                                /* Login */
                                flattrLoginWebView.url = controller.getFlattrLoginURL();
                                pageStack.push(flattrLoginPage);
                            }
                        }
                    }

                    SettingsSwitch {
                        id: flattrOnPlaySwitch
                        text: _('Auto-Flattr on playback')
                        onCheckedChanged: {
                            configProxy.flattrOnPlay = checked
                        }
                    }

                    SettingsHeader { text: _('gpodder.net') }

                    SettingsSwitch {
                        id: myGpoEnableSwitch
                        text: _('Enable synchronization')
                    }

                    Item { height: Config.largeSpacing; width: 1 }

                    SettingsLabel { text: _('Username') }
                    InputField { id: myGpoUsernameField; anchors.left: parent.left; anchors.right: parent.right }

                    Item { height: 1; width: 1 }

                    SettingsLabel { text: _('Password') }
                    InputField { id: myGpoPasswordField; anchors.left: parent.left; anchors.right: parent.right; echoMode: TextInput.Password }

                    Item { height: 1; width: 1 }

                    SettingsLabel { text: _('Device name') }
                    InputField { id: myGpoDeviceCaptionField; anchors.left: parent.left; anchors.right: parent.right }

                    Item { height: Config.largeSpacing; width: 1 }

                    Button {
                        text: _('Replace list on server')
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width * .8
                        onClicked: {
                            settingsPageClose.clicked()
                            controller.myGpoUploadList()
                        }
                    }

                    Item { height: Config.largeSpacing; width: 1 }

                    Button {
                        text: _('No account? Register here')
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width * .8
                        onClicked: Qt.openUrlExternally('http://gpodder.net/register/')
                    }
                }
            }
        }
    }

    Component.onCompleted: {
        theme.inverted = true
    }
}

