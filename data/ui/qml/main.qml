
import Qt 4.7

import 'config.js' as Config

Rectangle {
    id: main

    state: 'podcasts'

    color: "#203d64"

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

            Behavior on opacity { NumberAnimation { duration: 500 } }
            Behavior on scale { NumberAnimation { duration: 500 } }
        }

        Behavior on opacity { NumberAnimation { duration: 100 } }
        Behavior on scale { NumberAnimation { duration: 200 } }
    }

    EpisodeDetails {
        states: [
                State {
                    name: 'visible'
                    PropertyChanges {
                        target: episodeDetails
                        anchors.topMargin: 0
                    }
                    PropertyChanges {
                        target: listContainer
                        scale: .8
                        opacity: .5
                    }
                    StateChangeScript {
                        script: episodeDetails.startPlayback()
                    }
                },
                State {
                    name: 'hidden'
                    PropertyChanges {
                        target: episodeDetails
                        anchors.topMargin: parent.height
                    }
                    PropertyChanges {
                        target: listContainer
                        opacity: 1
                        scale: 1
                    }
                }
        ]

        state: 'hidden'

        id: episodeDetails
        opacity: (state == 'visible' || y > -height)?1:0
        clip: y != 0

        height: parent.height

        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
            topMargin: -height
        }

        Behavior on anchors.topMargin { NumberAnimation { duration: 200 } }
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
            anchors.left: parent.left
            anchors.top: parent.top
            width: Config.switcherWidth
            height: Config.headerHeight

            MouseArea {
                anchors.fill: parent
                onClicked: controller.switcher()
            }

            ScaledImage {
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
            text: episodeDetails.state == 'visible'?"Now playing":(main.state == 'episodes'?uidata.episodeListTitle:"gPodder")
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

            ScaledImage {
                anchors.centerIn: parent
                source: (main.state == 'podcasts' && episodeDetails.state == 'hidden')?'icons/close.png':'icons/back.png'
                rotation: (episodeDetails.state == 'visible')?-90:0
            }

            MouseArea {
                id: closeButtonMouseArea
                anchors.fill: parent
                onClicked: {
                    if (episodeDetails.state == 'visible') {
                        episodeDetails.state = 'hidden'
                    } else if (main.state == 'podcasts') {
                        controller.quit()
                    } else {
                        main.state = 'podcasts'
                    }
                }
            }
        }
    }

    NowPlayingThrobber {
        property bool shouldAppear: (episodeDetails.playing && episodeDetails.state == 'hidden' && !podcastList.moving && !episodeList.moving)

        id: nowPlayingThrobber
        anchors.bottom: parent.bottom
        anchors.right: parent.right
        opacity: shouldAppear?1:0

        onClicked: episodeDetails.state = 'visible'

        Behavior on opacity { NumberAnimation { duration: 100 } }
    }
}


