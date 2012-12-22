
import QtQuick 1.1

import com.nokia.meego 1.0

import 'config.js' as Config

Item {
    id: podcastList

    property alias model: listView.model
    property alias moving: listView.moving
    property bool hasItems: listView.visible

    signal podcastSelected(variant podcast)
    signal podcastContextMenu(variant podcast)
    signal subscribe

    Text {
        anchors.centerIn: parent
        color: '#aaa'
        font.pixelSize: 60
        font.weight: Font.Light
        horizontalAlignment: Text.AlignHCenter
        text: _('No podcasts.') + '\n' + _('Add your first podcast now.')
        visible: !listView.visible
        wrapMode: Text.WordWrap
        width: parent.width * .8

        MouseArea {
            anchors.fill: parent
            onClicked: podcastList.subscribe()
        }

    }

    Button {
        visible: !listView.visible
        text: _('Add a new podcast')
        onClicked: podcastList.subscribe()
        anchors {
            left: podcastList.left
            right: podcastList.right
            bottom: podcastList.bottom
            margins: 70
        }
    }

    PullDownHandle {
        target: listView
        pullDownText: _('Pull down to refresh')
        releaseText: _('Release to refresh')
        onRefresh: controller.updateAllPodcasts()
    }

    ListView {
        id: listView
        anchors.fill: parent
        visible: count > 1

        section.property: 'section'
        section.delegate: Item {
            height: Config.headerHeight
            Label {
                font.pixelSize: parent.height * .5
                wrapMode: Text.NoWrap
                text: section
                color: "#aaa"
                anchors {
                    leftMargin: Config.iconSize * 1.3 + Config.smallSpacing
                    bottom: parent.bottom
                    left: parent.left
                    right: parent.right
                }
            }
        }

        delegate: PodcastItem {
            onSelected: podcastList.podcastSelected(item)
            onContextMenu: podcastList.podcastContextMenu(item)
        }

        cacheBuffer: height
    }

    ScrollDecorator {
        flickableItem: listView
    }

}

