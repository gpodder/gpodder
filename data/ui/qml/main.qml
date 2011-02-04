
import Qt 4.7

import 'config.js' as Config

Rectangle {
    id: main

    state: 'podcasts'

    //OLD color: "#203d64"
    color: "#3b485b"

    Image {
        anchors.fill: parent
        source: 'podcastList/mask.png'
    }

    Image {
        anchors.fill: parent
        source: 'podcastList/noise.png'
    }

    function setCurrentEpisode(episode) {
        episodeDetails.episode = episode
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
            model: podcastModel
            opacity: 0

            anchors.fill: parent

            onPodcastSelected: controller.podcastSelected(podcast)
            onPodcastContextMenu: controller.podcastContextMenu(podcast)
            onAction: controller.action(action)

            Behavior on opacity { NumberAnimation { duration: 500 } }
            Behavior on scale { NumberAnimation { duration: 500 } }
        }

        EpisodeList {
            id: episodeList
            model: episodeModel
            opacity: 0

            anchors.fill: parent

            onEpisodeSelected: controller.episodeSelected(episode)
            onEpisodeContextMenu: controller.episodeContextMenu(episode)

            Behavior on opacity { NumberAnimation { duration: 500 } }
            Behavior on scale { NumberAnimation { duration: 500 } }
        }

        Behavior on opacity { NumberAnimation { duration: 100 } }
        Behavior on scale { NumberAnimation { duration: 200 } }
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
                StateChangeScript {
                    script: episodeDetails.startPlayback()
                }
            }
        ]

        transitions: Transition {
            AnchorAnimation { duration: 200 }
        }

        state: 'hidden'
        clip: true

        anchors {
            top: main.bottom
            left: main.left
            right: main.right
            bottom: main.bottom
        }
    }

    NowPlayingThrobber {
        property bool shouldAppear: (((episodeDetails.playing && !podcastList.moving && !episodeList.moving) || (episodeDetails.state == 'visible')) && (contextMenu.state != 'opened'))

        id: nowPlayingThrobber
        anchors.bottom: episodeDetails.top
        anchors.right: parent.right
        opacity: shouldAppear?1:0
        z: 10

        opened: (episodeDetails.state == 'visible')

        onClicked: {
            if (episodeDetails.state == 'visible') {
                episodeDetails.state = 'hidden'
            } else {
                episodeDetails.state = 'visible'
            }
        }

        Behavior on opacity { NumberAnimation { duration: 100 } }
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

        Behavior on opacity { NumberAnimation { duration: 200 } }

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
            AnchorAnimation { duration: 200 }
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
            anchors.right: closeButton.left
            clip: true
            text: (contextMenu.state == 'opened')?('Context menu'):(episodeDetails.state == 'visible'?"Now playing":(main.state == 'episodes'?uidata.episodeListTitle:"gPodder"))
            color: Qt.lighter(main.color, 4)
            font.pixelSize: parent.height * .5
            font.bold: false
        }

        Item {
            id: closeButton
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: taskSwitcher.width

            Rectangle {
                anchors.fill: parent
                color: 'white'
                opacity: closeButtonMouseArea.pressed?.3:0
            }

            ScaledIcon {
                anchors {
                    verticalCenter: parent.verticalCenter
                    right: parent.right
                    rightMargin: (parent.width * .8 - width) / 2
                }
                source: (main.state == 'podcasts' && episodeDetails.state == 'hidden' && contextMenu.state == 'closed')?'icons/close.png':'icons/back.png'
                rotation: (episodeDetails.state == 'visible')?-90:0
            }

            MouseArea {
                id: closeButtonMouseArea
                anchors.fill: parent
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

}


