import QtQuick 1.1
import QtDesktop 0.1

Window {
  id: item1
  width: 400
  height: 300

  TabFrame {
    id: tabgroup1
    anchors.bottom: button1.top
    anchors.right: parent.right
    anchors.left: parent.left
    anchors.top: parent.top

    TabBar {
      id: tabbar1
      anchors.fill: parent
      property string title: qsTr("General")

      Image {
        id: imgCover
        width: 100
        height: 100
        anchors.left: parent.left
        anchors.top: parent.top
        source: "qrc:/qtquickplugin/images/template_image.png"
      }

      TextField {
        id: entryTitle
        text: ""
        anchors.right: parent.right
        anchors.left: imgCover.right
        anchors.top: parent.top
      }

      CheckBox {
        id: cbSkipFeedUpdate
        text: "Disable feed updates (pause subscription)"
        anchors.right: parent.right
        anchors.left: imgCover.right
        anchors.top: entryTitle.bottom
      }

      Label {
        id: label_section
        text: qsTr("Section:")
        anchors.left: imgCover.right
        anchors.verticalCenter: combo_section.verticalCenter
      }

      ComboBox {
        id: combo_section
        anchors.right: button_add_section.left
        anchors.left: label_section.right
        anchors.top: cbSkipFeedUpdate.bottom
      }

      Button {
        id: button_add_section
        text: "Add"
        anchors.right: parent.right
        anchors.verticalCenter: combo_section.verticalCenter
      }

      TextArea {
        id: textarea1
        anchors.top: imgCover.bottom
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.left: parent.left
      }

    }

    TabBar {
      id: tabbar2
      anchors.fill: parent
      property string title: qsTr("Advanced")

      GroupBox {
        id: groupbox1
        anchors.right: parent.right
        anchors.left: parent.left
        anchors.top: parent.top
        title: "HTTP/FTP Authentication"

        Label {
          id: label2
          text: qsTr("Username:")
          anchors.left: parent.left
          anchors.verticalCenter: feedUsername.verticalCenter
        }
        TextField {
          id: feedUsername
          anchors.left: label2.right
          anchors.top: parent.top
          anchors.right: parent.right
        }

        Label {
          id: label3
          text: qsTr("Password:")
          anchors.left: parent.left
          anchors.verticalCenter: feedPassword.verticalCenter
        }
        TextField {
          id: feedPassword
          passwordMode: true
          anchors.top: feedUsername.bottom
          anchors.left: label3.right
          anchors.right: parent.right
        }
      }


      GroupBox {
        id: groupbox2
        anchors.right: parent.right
        anchors.left: parent.left
        anchors.top: groupbox1.bottom
        title: "Locations"

        Label {
          id: label4
          text: qsTr("Download to:")
          anchors.left: parent.left
          anchors.verticalCenter: labelDownloadTo.verticalCenter
        }

        TextField {
          id: labelDownloadTo
          anchors.top: parent.top
          anchors.left: label4.right
          anchors.right: parent.right
          readOnly: true
        }

        Label {
          id: label6
          text: qsTr("Website:")
          anchors.left: parent.left
          anchors.verticalCenter: labelWebsite.verticalCenter
        }

        TextField {
          id: labelWebsite
          anchors.left: label6.right
          anchors.top: labelDownloadTo.bottom
          anchors.right: btn_website.left
          readOnly: true
        }

        Button {
          id: btn_website
          text: "Website"
          anchors.right:  parent.right
          anchors.verticalCenter: labelWebsite.verticalCenter
        }
      }

    }
  }

  Button {
    id: button1
    x: 158
    y: 217
    width: 100
    text: "Button"
    anchors.right: parent.right
    anchors.bottom: parent.bottom
  }

}
