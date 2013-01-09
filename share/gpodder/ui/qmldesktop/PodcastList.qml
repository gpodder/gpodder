import QtQuick 1.1
import QtDesktop 0.1
import 'config.js' as Config

Item {
  id: podcastList
  height: childrenRect.height
  width: 1

  property alias model: listView.model
  property alias moving: listView.moving
  property alias currentIndex: listView.currentIndex
  property bool hasItems: listView.visible

  signal podcastSelected(variant podcast)
  signal podcastSelected2(variant index)
  signal podcastContextMenu(variant podcast)
  signal subscribe()

  Text {
    id: addFirstPodcast
    color: '#aaa'
    horizontalAlignment: Text.AlignHCenter
    text: _('No podcasts.') + '\n' + _('Add your first podcast now.')
    visible: !listView.visible

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
      top: addFirstPodcast.bottom
      left: podcastList.left
      right: podcastList.right
      margins: 70
    }
  }

  onPodcastSelected2: listView.currentIndex = index

  ListView {
    id: listView
    height: contentHeight
    width: parent.width
    visible: count > 1
    interactive: false

    highlightFollowsCurrentItem : true
    highlight: Rectangle {
      color: "lightsteelblue"
      width: listView.width
    }
    highlightMoveDuration: Config.fadeTransition
    currentIndex: -1

    section.property: 'section'
    section.delegate: Label {
      height: Config.headerHeight
      text: section
      font.bold: true
      verticalAlignment: Text.AlignBottom
      anchors {
        leftMargin: Config.smallSpacing
        left: parent.left
        right: parent.right
      }
    }

    delegate: PodcastItem {
      height: Config.listItemHeight
    }
    cacheBuffer: height
  }
}
