import QtQuick 1.1
import 'config.js' as Config

Item {
  id: episodeList
  height: childrenRect.height
  width: 1

  property string currentFilterText
  property string mainState

  onMainStateChanged: {
    // Don't remember contentY when leaving episode list
    listView.lastContentY = 0;
  }

  property alias model: listView.model
  property alias moving: listView.moving
  property alias count: listView.count
  property alias currentIndex: listView.currentIndex
  property string description: ""

  signal episodeContextMenu(variant episode)
  signal episodeItemChange(variant episode)

  signal activateFilter();

  function resetSelection() {
    listView.openedIndex = -1
  }

  Text {
    color: 'white'
    font.pixelSize: 30
    horizontalAlignment: Text.AlignHCenter
    text: '<big>' + _('No episodes') + '</big>' + '<br><small>' + _('Touch to change filter') + '</small>'
    visible: !listView.visible

    MouseArea {
      anchors.fill: parent
      onClicked: episodeList.activateFilter()
    }
  }

  ListView {
    id: listView
    width: parent.width
    height: contentHeight
    interactive: false
    currentIndex: -1
    visible: count > 0
    property real lastContentY: 0

    highlightMoveDuration: Config.fadeTransition
    highlightFollowsCurrentItem : true
    highlight: Rectangle {
      color: "lightsteelblue"
      width: episodeList.width
    }

    delegate: EpisodeItem {
      id: episodeItem

      width: listView.width
      height: Config.listItemHeight
      onSelected: {
        description = item.qdescription
        episodeList.episodeItemChange(item)
      }
      onContextMenu: episodeList.episodeContextMenu(item)
    }

    onContentYChanged: {
      // Keep Y scroll position when deleting episodes (bug 1660)
      if (contentY === 0) {
        if (lastContentY > 0) {
          contentY = lastContentY;
        }
      } else {
        if (episodeList.mainState === 'episodes') {
          // Only store scroll position when the episode list is
          // shown (avoids overwriting it in onMainStateChanged)
          lastContentY = contentY;
        }
      }
    }
  }
}

