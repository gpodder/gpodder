
import Qt 4.7

import 'config.js' as Config

Item {
    id: nowPlayingThrobber

    property bool opened
    property string caption: ''
    signal clicked

    height: Config.headerHeight
    width: icon.width + (opened?0:text.width)

    Behavior on width { NumberAnimation { duration: Config.slowTransition } }

    MouseArea {
        anchors.fill: parent
        onPressed: {
            nowPlayingThrobber.clicked()
        }
    }

    Image {
        id: icon

        source: 'artwork/nowplaying-tab.png'

        height: parent.height
        width: Config.switcherWidth

        ScaledIcon {
            anchors {
                verticalCenter: parent.verticalCenter
                right: parent.right
                rightMargin: (parent.width * .8 - width) / 2
            }
            //rotation: (nowPlayingThrobber.opened)?-90:0
            //source: (nowPlayingThrobber.opened)?'artwork/back.png':'artwork/play.png'
            source: 'artwork/play.png'

            Behavior on rotation { NumberAnimation { duration: Config.quickTransition } }
        }
    }

    Rectangle {
        id: text
        height: parent.height
        color: 'black'
        width: ((message.text!='')?(Config.smallSpacing * 2):0) + Math.min(main.width - icon.width - Config.smallSpacing*2, message.paintedWidth)
        anchors.left: icon.right

        //width: nowPlayingThrobber.opened?0:(Config.smallSpacing * 2 + message.width)
        //clip: true
        //Behavior on width { PropertyAnimation { duration: Config.quickTransition } }

        Text {
            id: message
            anchors.leftMargin: text!=''?Config.smallSpacing:0
            anchors.rightMargin: text!=''?Config.smallSpacing:0
            anchors.verticalCenter: parent.verticalCenter
            color: 'white'
            font.pixelSize: 20 * Config.scale
            //text: nowPlayingThrobber.opened?'':nowPlayingThrobber.caption
            text: ''
        }
    }
}

