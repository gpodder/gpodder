import QtQuick 1.1
import QtDesktop 0.1

import 'config.js' as Config
import 'util.js' as Util

Window {
  id: podcastDirectory

  width: Config.windowWidth
  height: Config.windowHeight

  property int checkboxWidth: 20
  property int channelChooserId: 0
  property int topPodcastsChooserId: 1
  property int youTubeChooserId: 2

  Component.onCompleted: {
    myController.viewCreated(podcastDirectory)
  }

  function updateModel(tab, model){
    tabGroup.tabs[tab].model = model
  }

  TabFrame {
    id: tabGroup
    anchors {
      bottom: buttonrow1.top
      right: parent.right
      left: parent.left
      top: parent.top
    }

    function getCurrentModel(){
      return tabs[current].model
    }

    TabBar {
      id: tabbar1
      anchors.fill: parent
      property string title: Util._("&OPML/Search")
      property alias model: channelChooserList.model

      Component.onCompleted: model = myController.getModel(channelChooserId)

      TextField {
        id: entryURL
        anchors {
          right: btnDownloadOpml.left
          left: parent.left
          top: parent.top
        }
        text: myController.getInitialOMPLUrl()

        onTextChanged: {
          btnDownloadOpml.text = myController.on_entryURL_changed(text)
        }
      }

      Button {
        id: btnDownloadOpml
        text: Util._("Download")
        anchors.right: parent.right
        anchors.verticalCenter: entryURL.verticalCenter
        onClicked: {
          myController.download_opml_file(entryURL.text)
        }
      }

      PodcastDirecrotyList {
        id: channelChooserList
        anchors {
          top: entryURL.bottom
          right: parent.right
          bottom: parent.bottom
          left: parent.left
        }

        onVisibleChanged: {
          if (visible != false && model === undefined)
            model = myController.getModel(channelChooserId)
        }
      }
    }

    PodcastDirecrotyList {
      id:topPodcastsChooserList
      anchors.fill: parent
      property string title: Util._("Top &podcasts")

      onVisibleChanged: {
        if (visible != false && model === undefined)
          model = myController.getModel(topPodcastsChooserId)
      }
    }

    TabBar {
      id: tabbar2
      anchors.fill: parent
      property string title: Util._("&YouTube")
      property alias model: youtubeList.model

      TextField {
        id: entryYoutubeSearch
        anchors.right: btnSearchYouTube.left
        anchors.top: parent.top
        anchors.left: parent.left
      }

      Button {
        id: btnSearchYouTube
        text: Util._("Search")
        anchors.right: parent.right
        anchors.verticalCenter: entryYoutubeSearch.verticalCenter

        onClicked: myController.on_searchYouTube(entryYoutubeSearch.text)
      }

      PodcastDirecrotyList {
        id: youtubeList
        anchors {
          top: entryYoutubeSearch.bottom
          left: parent.left
          right: parent.right
          bottom: parent.bottom
        }
      }
    }
  }

  ButtonRow {
    id: buttonrow1
    anchors.right: parent.right
    anchors.bottom: parent.bottom

    Button {
      id: btnSelectAll
      text: Util._("Select All")
      onClicked: tabGroup.getCurrentModel().setCheckedAll(true)
    }

    Button {
      id: btnSelectNone
      text: Util._("Select None")
      onClicked: tabGroup.getCurrentModel().setCheckedAll(false)
    }

    ToolButton {
      id: btnCancel
      text: iconName ? "" : Util._("Cancel")
      iconName: "window-close"
      onClicked: myController.close()
    }

    ToolButton {
      id: btnOK
      text: iconName ? "" : Util._("Add")
      iconName: "list-add"
      onClicked: myController.on_btnOK_clicked(tabGroup.getCurrentModel())
    }
  }
}
