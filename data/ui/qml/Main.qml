
import Qt 4.7

import 'config.js' as Config

Rectangle {
    id: main
    focus: true

    property alias podcastModel: podcastList.model
    property alias episodeModel: episodeList.model
    property alias currentEpisode: showNotes.episode

    property bool playing: false // XXX: Re-integrate later
    //property alias playing: showNotes.playing

    Keys.onPressed: {
        console.log(event.key)
        if (event.key == Qt.Key_Escape) {
            if (contextMenu.state == 'opened') {
                contextMenu.close()
            } else if (main.state == 'episodes') {
                main.state = 'podcasts'
            }
        }
        if (event.key == Qt.Key_F && event.modifiers & Qt.ControlModifier) {
            searchButton.clicked()
        }
    }

    width: 800
    height: 480

    state: 'podcasts'
    color: Config.baseColor

    Behavior on color { ColorAnimation { duration: 5000 } }
    Image {
        anchors.fill: parent
        source: 'artwork/mask.png'
    }

    Image {
        anchors.fill: parent
        source: 'artwork/noise.png'
    }

    function openShowNotes(episode) {
        showNotes.episode = episode
        main.state = 'shownotes'
    }

    function openContextMenu(items) {
        contextMenu.subscribeMode = false
        contextMenu.state = 'opened'
        contextMenu.items = items
    }

    states: [
        State {
            name: 'podcasts'
            PropertyChanges {
                target: podcastList
                opacity: 1
            }
            PropertyChanges {
                target: episodeList
                anchors.leftMargin: 100
                opacity: 0
            }
            PropertyChanges {
                target: showNotes
                opacity: 0
            }
        },
        State {
            name: 'episodes'
            PropertyChanges {
                target: episodeList
                opacity: 1
            }
            PropertyChanges {
                target: podcastList
                opacity: 0
                anchors.leftMargin: -100
            }
            PropertyChanges {
                target: showNotes
                opacity: 0
                scale: .8
            }
        },
        State {
            name: 'shownotes'
            PropertyChanges {
                target: listContainer
                opacity: 0
            }
            PropertyChanges {
                target: showNotes
                opacity: 1
                scale: 1
            }
        }
    ]

    Item {
        id: listContainer
        anchors.fill: parent

        PodcastList {
            id: podcastList
            opacity: 0

            anchors.fill: parent

            onPodcastSelected: controller.podcastSelected(podcast)
            onPodcastContextMenu: controller.podcastContextMenu(podcast)

            Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
            Behavior on anchors.leftMargin { NumberAnimation { duration: Config.slowTransition } }
        }

        EpisodeList {
            id: episodeList

            opacity: 0

            anchors.fill: parent

            onEpisodeContextMenu: controller.episodeContextMenu(episode)

            Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
            Behavior on anchors.leftMargin { NumberAnimation { duration: Config.slowTransition } }
        }

        Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
        Behavior on scale { NumberAnimation { duration: Config.fadeTransition } }
    }

    ShowNotes {
        id: showNotes

        anchors {
            left: parent.left
            right: parent.right
            top: titleBar.bottom
            bottom: parent.bottom

            leftMargin: Config.largeSpacing * 2
            rightMargin: Config.largeSpacing * 2
            topMargin: Config.largeSpacing * 2
            bottomMargin: Config.largeSpacing * 2
        }

        Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
        Behavior on scale { NumberAnimation { duration: Config.slowTransition; easing.type: Easing.InSine } }
    }

    NowPlayingThrobber {
        property bool shouldAppear: contextMenu.state != 'opened'

        id: nowPlayingThrobber
        anchors.bottom: mediaPlayer.top
        anchors.right: parent.right
        opacity: shouldAppear
        z: 10

        opened: false
        caption: (mediaPlayer.episode!=undefined)?mediaPlayer.episode.qtitle:''

        onClicked: { opened = !opened }

        Behavior on opacity { NumberAnimation { duration: Config.quickTransition } }
    }

    MediaPlayer {
        id: mediaPlayer
        visible: nowPlayingThrobber.opened

        anchors.top: parent.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.topMargin: nowPlayingThrobber.opened?(mediaPlayer.fullscreen?-parent.height:-100):0

        //episode: main.currentEpisode
        //episodeDetails.startPlayback()

        Behavior on anchors.topMargin { PropertyAnimation { duration: Config.slowTransition } }
    }

    ContextMenu {
        id: contextMenu

        width: parent.width
        opacity: 0

        anchors {
            top: parent.top
            bottom: parent.bottom
        }

        onClose: contextMenu.state = 'closed'
        onResponse: controller.contextMenuResponse(index)

        state: 'closed'

        Behavior on opacity { NumberAnimation { duration: Config.fadeTransition } }

        states: [
            State {
                name: 'opened'
                PropertyChanges {
                    target: contextMenu
                    opacity: 1
                }
                AnchorChanges {
                    target: contextMenu
                    anchors.right: main.right
                }
            },
            State {
                name: 'closed'
                PropertyChanges {
                    target: contextMenu
                    opacity: 0
                }
                AnchorChanges {
                    target: contextMenu
                    anchors.right: main.left
                }
                StateChangeScript {
                    script: controller.contextMenuClosed()
                }
            }
        ]

        transitions: Transition {
            AnchorAnimation { duration: Config.slowTransition }
        }
    }

    Item {
        id: titleBar
        height: taskSwitcher.height
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top

        anchors.topMargin: mediaPlayer.fullscreen?-height:0
        opacity: mediaPlayer.fullscreen?0:1

        Behavior on opacity { PropertyAnimation { } }
        Behavior on anchors.topMargin { PropertyAnimation { } }

        Rectangle {
            anchors.fill: parent
            color: "black"
            opacity: .6

            MouseArea {
                // clicks should not fall through!
                anchors.fill: parent
            }
        }

        Item {
            id: taskSwitcher
            visible: contextMenu.state != 'opened' && Config.hasTaskSwitcher
            anchors.left: parent.left
            anchors.top: parent.top
            width: Config.switcherWidth
            height: Config.headerHeight

            MouseArea {
                anchors.fill: parent
                onClicked: controller.switcher()
            }

            ScaledIcon {
                anchors {
                    verticalCenter: parent.verticalCenter
                    left: parent.left
                    leftMargin: (parent.width * .8 - width) / 2
                }
                source: 'artwork/switch.png'
            }
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: taskSwitcher.visible?taskSwitcher.right:taskSwitcher.left
            anchors.leftMargin: (contextMenu.state == 'opened')?(Config.largeSpacing):(Config.hasTaskSwitcher?0:Config.largeSpacing)
            anchors.right: searchButton.visible?searchButton.left:searchButton.right
            clip: true
            text: (contextMenu.state == 'opened')?(contextMenu.subscribeMode?'Add a new podcast':'Context menu'):((main.state == 'episodes' || main.state == 'shownotes')?controller.episodeListTitle:"gPodder")
            onTextChanged: controller.titleChanged(text)
            color: 'white'
            font.pixelSize: parent.height * .5
            font.bold: false
        }

        TitlebarButton {
            id: searchButton
            anchors.right: closeButton.visible?closeButton.left:closeButton.right

            source: 'artwork/subscriptions.png'

            onClicked: contextMenu.showSubscribe()

            visible: (contextMenu.state == 'closed' && main.state == 'podcasts')
        }

        TitlebarButton {
            id: closeButton
            anchors.right: parent.right
            visible: Config.hasCloseButton || main.state != 'podcasts' || main.state == 'shownotes' || contextMenu.state != 'closed'

            source: (main.state == 'podcasts' && contextMenu.state == 'closed')?'artwork/close.png':'artwork/back.png'
            rotation: 0 // XXX (episodeDetails.state == 'visible' && contextMenu.state == 'closed')?-90:0

            onClicked: {
                if (contextMenu.state == 'opened') {
                    contextMenu.state = 'closed'
                } else if (main.state == 'podcasts') {
                    //episodeDetails.stop()
                    controller.quit()
                } else if (main.state == 'episodes') {
                    main.state = 'podcasts'
                } else if (main.state == 'shownotes') {
                    main.state = 'episodes'
                }
            }
        }
    }

    function showMessage(message) {
        messageDialogText.text = message
        messageDialog.opacity = 1
    }

    Item {
        id: messageDialog
        anchors.fill: parent
        opacity: 0
        z: 20

        Behavior on opacity { PropertyAnimation { } }

        Rectangle {
            anchors.fill: parent
            color: '#ee000000'
        }

        Text {
            id: messageDialogText
            anchors.centerIn: parent
            color: 'white'
            font.pixelSize: 20
            font.bold: true
        }

        MouseArea {
            anchors.fill: parent
            onClicked: messageDialog.opacity = 0
        }
    }
}

