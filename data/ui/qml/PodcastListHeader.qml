
import Qt 4.7

import 'config.js' as Config

Item {
    id: xxx
    anchors.left: parent.left
    anchors.right: parent.right
    height: Config.headerHeight * 2 + Config.smallSpacing * 2
    state: 'b'

    states: [
        State {
            name: 'b'
            PropertyChanges {
                target: xxx
                height: Config.headerHeight
            }
        },
        State {
            name: 'a'
        }
    ]

    Behavior on height { PropertyAnimation { } }

    Row {
        opacity: parent.state == 'a'?1:0
        Behavior on opacity { PropertyAnimation { } }

        anchors.fill: parent
        anchors.topMargin: Config.headerHeight + Config.smallSpacing
        anchors.leftMargin: spacing
        spacing: 10

        Rectangle {
            color: '#80000000'
            width: (parent.width - parent.spacing*(parent.children.length))/parent.children.length
            height: Config.headerHeight
        }

        Rectangle {
            color: '#80000000'
            width: (parent.width - parent.spacing*(parent.children.length))/parent.children.length
            height: Config.headerHeight
        }

        Rectangle {
            color: m3.pressed?'#000000':'#80000000'
            width: (parent.width - parent.spacing*(parent.children.length))/parent.children.length
            height: Config.headerHeight

            Text {
                color: 'white'
                anchors.centerIn: parent
                text: _('Update')
                font.pixelSize: 20
            }

            MouseArea {
                id: m3
                anchors.fill: parent
                onClicked: {
                    xxx.state = (xxx.state == 'a')?'b':'a'
                }
            }
        }
    }
}

