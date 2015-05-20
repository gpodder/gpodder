
import QtQuick 1.1
import QtWebKit 1.0

import org.gpodder.qmlui 1.0

import 'config.js' as Config

WindowWindow {
    id: rootWindow
    property variant main: mainObject

    function _(x) {
        return controller.translate(x)
    }

    InfoBanner {
        id: infoBanner
    }

    initialPage: PagePage {
        id: mainPage
        listview: mainObject.podcastListView

        lockToPortrait: !configProxy.autorotate

        actions: [
            Action {
                text: _('Now playing')
                onClicked: mainObject.clickPlayButton();
            },
            Action {
                text: _('Check for new episodes')
                onClicked: controller.updateAllPodcasts();
            },
            Action {
                text: _('Add podcast')
                onClicked: mainObject.clickSearchButton();
            },
            Action {
                text: _('Settings')
                onClicked: {
                    settingsPage.loadSettings();
                    pageStack.push(settingsPage);
                }
            },
            Action {
                text: _('About gPodder')
                onClicked: pageStack.push(aboutBox);
            }
        ]

        Main {
            id: mainObject
            anchors.fill: parent
        }
    }

    PagePage {
        id: subscribePage
        lockToPortrait: mainPage.lockToPortrait

        Subscribe {
            anchors.fill: parent

            onSubscribe: {
                controller.addSubscriptions(urls);
                pageStack.pop();
            }
        }
    }

    PagePage {
        id: showNotesPage
        lockToPortrait: mainPage.lockToPortrait

        ShowNotes {
            id: showNotes

            anchors.fill: parent

            Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
            Behavior on anchors.leftMargin { NumberAnimation { duration: Config.slowTransition } }
        }

        /*actions: [
            Action {
                text: controller.flattrButtonText
                onClicked: controller.flattrEpisode(showNotes.episode);
            }
        ]

        Connections {
            target: mainObject
            onShowNotesEpisodeChanged: {
                controller.updateFlattrButtonText(showNotes.episode);
            }
        }*/
    }

    PagePage {
        id: aboutBox
        property color textColor: 'white'
        lockToPortrait: true

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

        ScrollScroll {
            flickable: aboutFlickable
        }
    }

    PagePage {
        id: flattrLoginPage
        lockToPortrait: mainPage.lockToPortrait

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


    PagePage {
        id: myGpoLoginPage
        lockToPortrait: mainPage.lockToPortrait

        onClosed: {
            controller.myGpoUsername = myGpoUsernameField.text
            controller.myGpoPassword = myGpoPasswordField.text
            controller.myGpoDeviceCaption = myGpoDeviceCaptionField.text
        }

        Item {
            id: myGpoLoginContent
            anchors.fill: parent

            Flickable {
                anchors.fill: parent
                anchors.margins: Config.largeSpacing
                contentHeight: myGpoLoginColumn.height

                Column {
                    id: myGpoLoginColumn
                    anchors.fill: parent
                    spacing: 4

                    Label {
                        text: _('gPodder.net Login')
                        font.pixelSize: 40
                        anchors.right: parent.right
                    }

                    SettingsHeader { text: _('Credentials') }

                    SettingsLabel { text: _('Username') }
                    InputField { id: myGpoUsernameField; anchors.left: parent.left; anchors.right: parent.right }

                    Item { height: 1; width: 1 }

                    SettingsLabel { text: _('Password') }
                    InputField { id: myGpoPasswordField; anchors.left: parent.left; anchors.right: parent.right; echoMode: TextInput.Password }

                    Item { height: 1; width: 1 }

                    SettingsLabel { text: _('Device name') }
                    InputField { id: myGpoDeviceCaptionField; anchors.left: parent.left; anchors.right: parent.right }

                }
            }
        }
}

    PagePage {
        id: settingsPage
        lockToPortrait: mainPage.lockToPortrait

        property bool myGpoUserPassFilled: controller.myGpoUsername != '' && controller.myGpoPassword != ''

        function loadSettings() {
            settingsAutorotate.checked = configProxy.autorotate
            settingsIndexing.checked = trackerMinerConfig.get_index_podcasts()

            flattrOnPlaySwitch.checked = configProxy.flattrOnPlay

            myGpoEnableSwitch.checked = controller.myGpoEnabled
            myGpoUsernameField.text = controller.myGpoUsername
            myGpoPasswordField.text = controller.myGpoPassword
            myGpoDeviceCaptionField.text = controller.myGpoDeviceCaption

            youTubeAPIKey.text = controller.youTubeAPIKey
        }

        onClosed: {
            controller.myGpoEnabled = myGpoEnableSwitch.checked && myGpoUserPassFilled;
            controller.saveMyGpoSettings();
            controller.youTubeAPIKey = youTubeAPIKey.text;
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
                        font.pixelSize: 40
                        anchors.right: parent.right
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

                    SettingsHeader { text: _('YouTube') }

                    Label {
                        text: _('API Key (v3):')
                    }

                    InputField { id: youTubeAPIKey; anchors.left: parent.left; anchors.right: parent.right }

                    Button {
                        text: _('Migrate subscriptions')
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width * .8
                        onClicked: {
                            controller.youTubeAPIKey = youTubeAPIKey.text;
                            controller.migrateYouTubeSubscriptions();
                        }
                        enabled: youTubeAPIKey.text !== ''
                    }

                    SettingsHeader { text: _('gpodder.net') }

                    SettingsSwitch {
                        id: myGpoEnableSwitch
                        text: _('Enable synchronization')
                    }

                    Item { height: Config.largeSpacing; width: 1 }

                    Button {
                        text: {
                            if (settingsPage.myGpoUserPassFilled) {
                                _('Sign out')
                            } else {
                                _('Sign in to gPodder.net')
                            }
                        }
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width * .8
                        onClicked: {
                            if (settingsPage.myGpoUserPassFilled) {
                                /* Logout */
                                controller.myGpoPassword = '';
                                myGpoPasswordField.text = '';
                            } else {
                                /* Login */
                                pageStack.push(myGpoLoginPage);
                            }
                        }
                    }
                    Item { height: Config.largeSpacing; width: 1 }

                    Button {
                        text: _('Replace list on server')
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width * .8
                        visible: settingsPage.myGpoUserPassFilled
                        onClicked: {
                            pageStack.pop();
                            controller.myGpoUploadList();
                        }
                    }

                    Button {
                        text: _('No account? Register here')
                        visible: ! settingsPage.myGpoUserPassFilled
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

