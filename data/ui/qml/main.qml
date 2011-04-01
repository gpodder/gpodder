
import Qt 4.7

import 'config.js' as Config

import "test"

Rectangle {
    id: main
    focus: true

    property alias podcastModel: podcastList.model
    property alias episodeModel: episodeList.model
    property alias currentEpisode: episodeDetails.episode

    property variant controller
    controller: Controller { main: main }

    property list<Podcast> podcastListExample
    podcastListExample: [
        Podcast { qdownloaded: 1; qsection: 'audio' },
        Podcast { qdownloaded: 0; qsection: 'audio' },
        Podcast { qdownloaded: 0; qsection: 'video' },
        Podcast { qdownloaded: 0; qsection: 'other' },
        Podcast {},
        Podcast { qnew: 2 },
        Podcast { qnew: 9 },
        Podcast {}
    ]

    property list<Episode> episodeListExample
    episodeListExample: [
        Episode {},
        Episode {},
        Episode { qfiletype: 'video' },
        Episode {},
        Episode {},
        Episode { qfiletype: 'video' },
        Episode {},
        Episode {},
        Episode { qfiletype: 'download' },
        Episode {},
        Episode {}
    ]

    Keys.onPressed: {
        console.log(event.key)
        if (event.key == Qt.Key_Escape) {
            if (contextMenu.state == 'opened') {
                contextMenu.close()
            } else if (episodeDetails.state == 'visible') {
                episodeDetails.state = 'hidden'
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
        source: 'podcastList/mask.png'
    }

    Image {
        anchors.fill: parent
        source: 'podcastList/noise.png'
    }

    function setCurrentEpisode() {
        episodeDetails.startPlayback()
        episodeDetails.state = 'visible'
    }

    function openContextMenu(items) {
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
                scale: .9
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
                scale: 1.2
                opacity: 0
            }
        }
    ]

    Item {
        id: listContainer
        anchors.fill: parent

        PodcastList {
            id: podcastList
            opacity: 0
            model: podcastListExample

            anchors.fill: parent

            onPodcastSelected: controller.podcastSelected(podcast)
            onPodcastContextMenu: controller.podcastContextMenu(podcast)

            Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
            Behavior on scale { NumberAnimation { duration: Config.slowTransition } }
        }

        EpisodeList {
            id: episodeList
            opacity: 0
            model: episodeListExample

            anchors.fill: parent

            onEpisodeSelected: controller.episodeSelected(episode)
            onEpisodeContextMenu: controller.episodeContextMenu(episode)

            Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
            Behavior on scale { NumberAnimation { duration: Config.slowTransition } }
        }

        Behavior on opacity { NumberAnimation { duration: Config.slowTransition } }
        Behavior on scale { NumberAnimation { duration: Config.fadeTransition } }
    }

    EpisodeDetails {
        id: episodeDetails

        states: [
            State {
                name: 'hidden'
                AnchorChanges {
                    target: episodeDetails
                    anchors.top: main.bottom
                }
                PropertyChanges {
                    target: listContainer
                    opacity: 1
                    scale: 1
                }
            },
            State {
                name: 'visible'
                AnchorChanges {
                    target: episodeDetails
                    anchors.top: titleBar.bottom
                }
                PropertyChanges {
                    target: listContainer
                    scale: .8
                    opacity: .5
                }
            }
        ]

        transitions: Transition {
            SequentialAnimation {
                ScriptAction { script: episodeDetails.opacity = 1 }
                AnchorAnimation { duration: Config.slowTransition }
                ScriptAction { script: episodeDetails.opacity = (episodeDetails.state=='visible') }
            }
        }

        state: 'hidden'
        opacity: 0

        onStateChanged: {
            if (state == 'visible' && episode == undefined) {
                controller.loadLastEpisode()
            }
        }

        anchors {
            top: main.bottom
            left: main.left
            right: main.right
            bottom: main.bottom
        }
    }

    NowPlayingThrobber {
        property bool shouldAppear: contextMenu.state != 'opened'

        id: nowPlayingThrobber
        anchors.bottom: episodeDetails.top
        anchors.right: parent.right
        opacity: shouldAppear
        z: 10

        opened: (episodeDetails.state == 'visible')

        onClicked: {
            if (episodeDetails.state == 'visible') {
                episodeDetails.state = 'hidden'
            } else {
                episodeDetails.state = 'visible'
            }
        }

        Behavior on opacity { NumberAnimation { duration: Config.quickTransition } }
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
            visible: contextMenu.state != 'opened'
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
                source: 'icons/switch.png'
            }
        }

        ShadowText {
            anchors.verticalCenter: parent.verticalCenter
            anchors.left: taskSwitcher.right
            anchors.right: searchButton.left
            clip: true
            text: (contextMenu.state == 'opened')?('Context menu'):(episodeDetails.state == 'visible'?("Now playing - "+((currentEpisode!=undefined)?currentEpisode.qpositiontext:'No episode')):(main.state == 'episodes'?controller.episodeListTitle:"gPodder"))
            onTextChanged: controller.titleChanged(text)
            color: Qt.lighter(main.color, 4)
            font.pixelSize: parent.height * .5
            font.bold: false
        }

        TitlebarButton {
            id: searchButton
            anchors.right: closeButton.left

            source: 'icons/subscriptions.png'

            onClicked: controller.searchButtonClicked()

            visible: contextMenu.state == 'closed'
        }

        TitlebarButton {
            id: closeButton
            anchors.right: parent.right

            source: (main.state == 'podcasts' && episodeDetails.state == 'hidden' && contextMenu.state == 'closed')?'icons/close.png':'icons/back.png'
            rotation: (episodeDetails.state == 'visible' && contextMenu.state == 'closed')?-90:0

            onClicked: {
                if (contextMenu.state == 'opened') {
                    contextMenu.state = 'closed'
                } else if (episodeDetails.state == 'visible') {
                    episodeDetails.state = 'hidden'
                } else if (main.state == 'podcasts') {
                    episodeDetails.stop()
                    controller.quit()
                } else {
                    main.state = 'podcasts'
                }
            }
        }
    }
}


