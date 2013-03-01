
import QtQuick 1.1
import Sailfish.Silica 1.0

Item {
    id: settingsSwitch
    property alias text: theLabel.text
    property alias checked: theSwitch.checked

    width: parent.width
    height: theSwitch.height

    Label {
        id: theLabel
        anchors.left: parent.left
        anchors.right: theSwitch.left
        elide: Text.ElideRight
        anchors.verticalCenter: parent.verticalCenter
    }

    Switch {
        id: theSwitch
        anchors.right: parent.right
    }
}

