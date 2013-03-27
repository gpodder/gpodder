import QtQuick 1.1
import QtDesktop 0.1

import 'config.js' as Config
import 'util.js' as Util

Item {
  id: episodeList
  width: 1

  property string currentFilterText
  property string mainState

  onMainStateChanged: {
    // Don't remember contentY when leaving episode list
    listView.lastContentY = 0;
  }

  property alias model: listView.model
  //  property alias moving: listView.moving
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
    font.pixelSize: 30
    horizontalAlignment: Text.AlignHCenter
    text: '<big>' + Util._("No episodes") + '</big>'
    visible: !listView.visible

    MouseArea {
      anchors.fill: parent
      onClicked: episodeList.activateFilter()
    }
  }

  TableView {
    id: listView
    anchors.fill: parent
    visible: count > 0
    property int padding: Config.smallSpacing

    onCurrentIndexChanged: {
      var episode = model.get(currentIndex)
      if (episode != null){
        description = episode.qdescription
        episodeItemChange(episode)
      }
    }

    TableColumn {
      role: "modelData"
      title: "Title"
      width: 120
      delegate: EpisodeColumn {
        padding: listView.padding
        text: itemValue.qtitle
        fontBold: true
      }
    }

    TableColumn {
      role: "modelData"
      title: "Size"
      width: 75
      delegate: EpisodeColumn {
        padding: listView.padding
        text: itemValue.qfilesize
      }
    }

    TableColumn {
      role: "modelData"
      title: "Duration"
      width: 120
      delegate: EpisodeColumn {
        padding: listView.padding
        text: itemValue.qduration ? Util.formatDuration(itemValue.qduration) : ''
      }
    }

    TableColumn {
      role: "modelData"
      title: "Date"
      width: 75
      delegate: EpisodeColumn {
        padding: listView.padding
        text: itemValue.qpubdate
      }
    }
  }
}
