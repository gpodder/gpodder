
import Qt 4.7

import 'config.js' as Config

Image {
    width: sourceSize.width / Config.scale
    height: sourceSize.height / Config.scale
    smooth: true
}

