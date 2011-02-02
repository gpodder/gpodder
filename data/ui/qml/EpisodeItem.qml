import Qt 4.7

Image {
    id: episodeItem
    signal episodeSelected(variant episode)

    width: parent.width
    source: 'episodeList/bg.png'

    Image {
        id: icon
        source: 'episodeList/' + model.episode.qfiletype + '.png'
        width: 40
        height: 40
        opacity: model.episode.qdownloaded?1:.1
        anchors.verticalCenter: parent.verticalCenter
        anchors.left: parent.left
        anchors.leftMargin: 15
    }

    ShadowText {
        text: model.episode.qtitle
        color: model.episode.qnew?"white":"#888"
        font.pointSize: 16
        font.bold: false //model.episode.qnew
        anchors.left: icon.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.right: parent.right
        anchors.leftMargin: 15
        elide: Text.ElideRight
    }

    MouseArea {
        anchors.fill: parent
        onClicked: episodeItem.episodeSelected(model.episode)
    }
}

