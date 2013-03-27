import QtQuick 1.1
import QtDesktop 0.1

import 'config.js' as Config
import "util.js" as Util

ToolBar {
  id: toolbar
  anchors.right: parent.right
  anchors.left: parent.left

  property bool aboutToHide: false
  property variant currentEpisode: undefined

  function toggleVisible(){
    aboutToHide = !aboutToHide
  }

  states: [
    State {
      name: "visible"; when: !aboutToHide
      PropertyChanges { target: toolbar; y:0 }
    },
    State {
      name: "hidden"; when: aboutToHide
      PropertyChanges { target: toolbar; y:-height}
    }
  ]

  transitions: Transition {
    SequentialAnimation {
      NumberAnimation {
        duration: Config.slowTransition
        properties: "y"
        easing.type: Easing.OutBack
      }
    }
  }

  ToolButton {
    id: toolDownload
    text: iconName ? "" : Util._("Download")
    anchors.left: parent.left
    anchors.verticalCenter: parent.verticalCenter
    iconName: "download"

    enabled: (currentEpisode!==undefined) ? (!currentEpisode.qdownloaded && !currentEpisode.qdownloading) : false
    onClicked: controller.downloadEpisode(currentEpisode)
  }

  ToolButton {
    id: toolPlay
    text: iconName ? "" : Util._("Play")
    anchors.left: toolDownload.right
    anchors.verticalCenter: parent.verticalCenter
    iconName: "media-playback-start"

    enabled: (currentEpisode!==undefined) ? (currentEpisode.qdownloaded) : false
    onClicked: controller.playback_selected_episodes(currentEpisode)
  }

  ToolButton {
    id: toolCancel
    text: iconName ? "" : Util._("Cancel")
    anchors.left: toolPlay.right
    anchors.verticalCenter: parent.verticalCenter

    enabled: (currentEpisode!==undefined) ? (!currentEpisode.qdownloaded && currentEpisode.qdownloading) : false
    onClicked: controller.cancelDownload(currentEpisode)
    iconName: "dialog-cancel"
  }

  ToolButton {
    id: toolPreferences
    text: iconName ? "" : Util._("Preferences")
    anchors.left: toolCancel.right
    anchors.verticalCenter: parent.verticalCenter
    onClicked: controller.createWindow(parent, "Preferences.qml")
    iconName: "preferences-system"
  }

  ToolButton {
    id: toolQuit
    text: iconName ? "" : Util._("Quit")
    anchors.left: toolPreferences.right
    anchors.verticalCenter: parent.verticalCenter
    onClicked: controller.quit()
    iconName: "application-exit"
  }
}
