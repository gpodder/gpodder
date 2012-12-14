import QtQuick 1.1
import QtDesktop 0.1

Window {
  id: configDialog
  width: 400
  height: 200
  spacing: 5

  TabFrame {
    id: tabgroup1
    anchors.bottom: buttonrow2.top
    anchors.right: parent.right
    anchors.left: parent.left
    anchors.top: parent.top
    anchors.bottomMargin: configDialog.spacing
    tabsVisible: true
    current: 0

    ScrollArea {
      id: extensions
      property string title: "Extensions"
      clip: true
      anchors.fill: parent

      Column {
        id: extensionsList
        anchors.right: parent.right
        anchors.left: parent.left
        anchors.rightMargin: 0
        anchors.leftMargin: 0
        spacing: configDialog.spacing
      }
    }

    TabBar {
      id: flattr_config
      property string title: "Flattr"
      anchors.fill: parent
    }

    TabBar {
      id: mygpo_config
      property string title: "Gpodder config"
      anchors.fill: parent
    }

    TabBar {
      id: updating
      property string title: "Updating"
      anchors.fill: parent
    }

    TabBar {
      id: downloads
      property string title: "Downloads"
      anchors.fill: parent
    }

    TabBar {
      id: devices
      property string title: "Devices"
      anchors.fill: parent
    }

    Grid {
      id: general
      property string title: "General"
      anchors.rightMargin: 0
      anchors.bottomMargin: 0
      anchors.leftMargin: 0
      anchors.topMargin: 0
      spacing: configDialog.spacing
      rows: 2
      columns: 3
      anchors.fill: parent

      Label {
        id: label1
        x: 30
        y: -35
        text: "Label"
      }

      Label {
        id: label2
        x: 30
        y: 19
        text: "Label"
      }

      ComboBox {
        id: combobox1
        x: 148
        y: 29
        width: 100
        hoveredText: ""
      }

      ComboBox {
        id: combobox2
        x: 160
        y: 80
        width: 100
        selectedText: "654654"
        selectedIndex: 0
      }
    }

  }

  ButtonRow {
    id: buttonrow2
    anchors.bottom: parent.bottom
    anchors.bottomMargin: configDialog.spacing
    anchors.right: parent.right
    anchors.rightMargin: configDialog.spacing
    spacing: configDialog.spacing
    exclusive: true

    Button {
      id: button1
      width: 100
      text: "Button"
    }

    Button {
      id: button2
      width: 100
      text: "Button"
    }
  }
}

