
import QtQuick 1.1

import org.gpodder.qmlui 1.0

import 'config.js' as Config

Item {
    id: podcastList

    property variant listview: listView
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

    ListList {
        headerText: 'gPodder'
        hasRefresh: true
        onRefresh: controller.updateAllPodcasts()

        id: listView
        anchors.fill: parent
        visible: count > 1

        section.property: 'section'
        section.delegate: Column {
            Text {
                font.pixelSize: Config.headerHeight * .5
                wrapMode: Text.NoWrap
                text: section
                color: Config.sectionHeaderColorText
                anchors {
                    left: parent.left
                    leftMargin: Config.smallSpacing
                }
            }

            Rectangle {
              height: 1
              border.width: 0
              color: Config.sectionHeaderColorLine
              width: listView.width - Config.largeSpacing
            }
        }

        delegate: PodcastItem {
            onSelected: podcastList.podcastSelected(item)
            onContextMenu: podcastList.podcastContextMenu(item)
        }

        cacheBuffer: height
    }

    ScrollScroll {
        flickable: listView
    }

}

