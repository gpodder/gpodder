
import Qt 4.7

import 'config.js' as Config

Item {
    id: cornerButton

    property bool opened
    property string icon: 'artwork/play.png'
    property string tab: 'artwork/nowplaying-tab.png'
    property string caption: ''
    property bool isLeftCorner: false
    signal clicked

    height: Config.headerHeight
    width: icon.width + (opened?0:text.width)

    Behavior on width { NumberAnimation { duration: Config.slowTransition } }

    Behavior on opacity { NumberAnimation { duration: Config.quickTransition } }

    anchors.bottomMargin: opened?-height:0
    Behavior on anchors.bottomMargin { NumberAnimation { duration: Config.slowTransition } }

    MouseArea {
        anchors.fill: parent
        onClicked: cornerButton.clicked()
    }

    Image {
        id: icon

        source: cornerButton.tab

        height: parent.height
        width: Config.switcherWidth

        ScaledIcon {
            anchors {
                verticalCenter: parent.verticalCenter
                right: parent.right
                rightMargin: cornerButton.isLeftCorner?(parent.width * .4):((parent.width * .8 - width) / 2)
            }
            source: cornerButton.icon

            Behavior on rotation { NumberAnimation { duration: Config.quickTransition } }
        }
    }

    Rectangle {
        id: text
        height: parent.height
        color: 'black'
        width: ((message.text!='')?(Config.smallSpacing * 2):0) + Math.min(main.width - icon.width - Config.smallSpacing*2, message.paintedWidth)
        anchors.left: icon.right

        //width: cornerButton.opened?0:(Config.smallSpacing * 2 + message.width)
        //clip: true
        //Behavior on width { PropertyAnimation { duration: Config.quickTransition } }

        Text {
            id: message
            anchors.leftMargin: text!=''?Config.smallSpacing:0
            anchors.rightMargin: text!=''?Config.smallSpacing:0
            anchors.verticalCenter: parent.verticalCenter
            color: 'white'
            font.pixelSize: 20 * Config.scale
            //text: cornerButton.opened?'':cornerButton.caption
            text: ''
        }
    }
}

