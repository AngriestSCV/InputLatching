import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Layouts 1.15

ApplicationWindow {
    id: window
    width: 520
    height: 700
    title: "Latch Input Tool"
    visible: true
    color: "#16171f"

    // ── Palette (themes default controls like ComboBox) ───────────────────────
    palette.window:           "#16171f"
    palette.windowText:       "#c9cad8"
    palette.base:             "#21222e"
    palette.alternateBase:    "#292a38"
    palette.button:           "#2e2f40"
    palette.buttonText:       "#c9cad8"
    palette.highlight:        "#7b68ee"
    palette.highlightedText:  "#ffffff"
    palette.text:             "#c9cad8"
    palette.mid:              "#3a3b52"
    palette.dark:             "#111218"
    palette.light:            "#3a3b52"

    // ── Colour tokens ─────────────────────────────────────────────────────────
    readonly property color clrSurface: "#21222e"
    readonly property color clrBorder:  "#2e2f42"
    readonly property color clrText:    "#c9cad8"
    readonly property color clrDim:     "#5a5b72"
    readonly property color clrAccent:  "#7b68ee"
    readonly property color clrGreen:   "#4eca8b"
    readonly property color clrRed:     "#f0506e"
    readonly property color clrOrange:  "#f5a623"

    // ── Inline components ─────────────────────────────────────────────────────
    component AppButton: Button {
        property color tint: clrAccent
        implicitHeight: 34
        contentItem: Text {
            text: parent.text
            color: "#ffffff"
            font.pixelSize: 12
            font.weight: Font.Medium
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: parent.down    ? Qt.darker(tint, 1.35)
                 : parent.hovered ? Qt.lighter(tint, 1.18)
                 :                  tint
            radius: 6
            Behavior on color { ColorAnimation { duration: 90 } }
        }
    }

    component SectionLabel: Label {
        color: clrDim
        font.pixelSize: 10
        font.letterSpacing: 1.8
        font.weight: Font.Bold
    }

    component Divider: Rectangle {
        Layout.fillWidth: true
        height: 1
        color: clrBorder
    }

    component KeyChip: Rectangle {
        property string keyText: ""
        property color chipColor: clrAccent
        color:        Qt.rgba(chipColor.r, chipColor.g, chipColor.b, 0.18)
        border.color: Qt.rgba(chipColor.r, chipColor.g, chipColor.b, 0.55)
        border.width: 1
        radius: 5
        width: chipLabel.implicitWidth + 14
        height: 22
        Label {
            id: chipLabel
            anchors.centerIn: parent
            text: keyText
            color: chipColor
            font.pixelSize: 11
            font.weight: Font.Medium
        }
    }

    component StatusPill: Rectangle {
        property bool active: false
        property string label: ""
        property color activeColor: clrGreen
        radius: 12
        implicitWidth: pillRow.implicitWidth + 22
        implicitHeight: 24
        color:        active ? Qt.rgba(activeColor.r, activeColor.g, activeColor.b, 0.16)
                             : Qt.rgba(clrDim.r,       clrDim.g,       clrDim.b,       0.12)
        border.color: active ? activeColor : clrBorder
        border.width: 1
        Behavior on color        { ColorAnimation { duration: 150 } }
        Behavior on border.color { ColorAnimation { duration: 150 } }
        Row {
            id: pillRow
            anchors.centerIn: parent
            spacing: 5
            Rectangle {
                width: 7; height: 7; radius: 4
                anchors.verticalCenter: parent.verticalCenter
                color: active ? activeColor : clrDim
                Behavior on color { ColorAnimation { duration: 150 } }
            }
            Label {
                text: label
                color: active ? activeColor : clrDim
                font.pixelSize: 12
                font.weight: Font.Medium
                Behavior on color { ColorAnimation { duration: 150 } }
            }
        }
    }

    // ── Root layout ───────────────────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 10

        // ── Device card ───────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: deviceCardCol.implicitHeight + 20
            color: clrSurface; radius: 10
            border.color: clrBorder; border.width: 1

            ColumnLayout {
                id: deviceCardCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                spacing: 8

                SectionLabel { text: "INPUT DEVICE" }

                RowLayout {
                    spacing: 6
                    ComboBox {
                        id: deviceCombo
                        model: bridge.deviceModel
                        Layout.fillWidth: true
                    }
                    AppButton {
                        text: "↻  Refresh"
                        implicitWidth: 90
                        tint: Qt.rgba(clrAccent.r, clrAccent.g, clrAccent.b, 0.55)
                        onClicked: bridge.refreshDevices()
                    }
                }

                RowLayout {
                    spacing: 6
                    AppButton {
                        text: "＋  Add Device"
                        Layout.fillWidth: true
                        onClicked: bridge.addDevice(deviceCombo.currentText)
                    }
                    AppButton {
                        text: "✕  Clear"
                        tint: clrRed
                        implicitWidth: 80
                        onClicked: bridge.clearDevices()
                    }
                }
            }
        }

        // ── Transport controls ────────────────────────────────────────────────
        RowLayout {
            spacing: 8
            Layout.fillWidth: true
            AppButton {
                text: "▶  Start";       tint: clrGreen;  Layout.fillWidth: true; onClicked: bridge.start()
            }
            AppButton {
                text: "■  Stop";        tint: clrRed;    Layout.fillWidth: true; onClicked: bridge.stop()
            }
            AppButton {
                text: "◎  Set Trigger"; tint: clrOrange; Layout.fillWidth: true; onClicked: bridge.beginSetTrigger()
            }
        }

        // ── State card ────────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: stateCol.implicitHeight + 20
            color: clrSurface; radius: 10
            border.color: clrBorder; border.width: 1

            ColumnLayout {
                id: stateCol
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 10 }
                spacing: 8

                // Status pills
                SectionLabel { text: "STATUS" }
                RowLayout {
                    spacing: 8
                    StatusPill {
                        active: bridge.running
                        label:  bridge.running ? "Running" : "Stopped"
                        activeColor: clrGreen
                    }
                    StatusPill {
                        active: bridge.triggerHeld
                        label:  "Trigger Held"
                        activeColor: clrOrange
                    }
                }

                // Trigger key
                RowLayout {
                    spacing: 6
                    Label { text: "Trigger key"; color: clrDim;  font.pixelSize: 12 }
                    Label { text: bridge.trigger; color: clrText; font.pixelSize: 12; font.weight: Font.Medium }
                }

                Divider {}

                // Latched keys
                SectionLabel { text: "LATCHED" }
                Flow {
                    Layout.fillWidth: true
                    spacing: 5
                    Repeater {
                        model: bridge.latched !== "None" ? bridge.latched.split(", ") : []
                        KeyChip { keyText: modelData; chipColor: clrAccent }
                    }
                    Label {
                        visible: bridge.latched === "None"
                        text: "—"; color: clrDim; font.pixelSize: 14
                    }
                }

                Divider {}

                // Auto-clicking
                SectionLabel { text: "AUTO-CLICKING" }
                Flow {
                    Layout.fillWidth: true
                    spacing: 5
                    Repeater {
                        model: bridge.autoClickKeys
                        KeyChip { keyText: modelData; chipColor: clrOrange }
                    }
                    Label {
                        visible: bridge.autoClickKeys.length === 0
                        text: "—"; color: clrDim; font.pixelSize: 14
                    }
                }

                Divider {}

                // Devices
                SectionLabel { text: "DEVICES" }
                Repeater {
                    model: bridge.loadedDevices
                    Label { text: modelData; color: clrText; font.pixelSize: 12 }
                }
                Label {
                    visible: bridge.loadedDevices.length === 0
                    text: "—"; color: clrDim; font.pixelSize: 14
                }
            }
        }

        // ── Log card ──────────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            color: "#111218"; radius: 10
            border.color: clrBorder; border.width: 1
            clip: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 10
                spacing: 6

                RowLayout {
                    SectionLabel { text: "LOG"; Layout.fillWidth: true }
                    AppButton {
                        text: "Clear"
                        implicitWidth: 58
                        implicitHeight: 24
                        tint: clrBorder
                        onClicked: logArea.clear()
                    }
                }

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Flickable {
                        id: logFlick
                        anchors { fill: parent; rightMargin: 10 }
                        contentWidth: width
                        contentHeight: logArea.implicitHeight
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds

                        TextArea {
                            id: logArea
                            width: logFlick.width
                            readOnly: true
                            wrapMode: Text.Wrap
                            color: "#6e8faa"
                            font.family: "monospace"
                            font.pixelSize: 11
                            background: null
                            leftPadding: 0
                        }

                        onContentHeightChanged:
                            contentY = Math.max(0, contentHeight - height)
                    }

                    // Scrollbar track
                    Rectangle {
                        anchors { right: parent.right; top: parent.top; bottom: parent.bottom }
                        width: 5
                        radius: 3
                        color: Qt.rgba(clrDim.r, clrDim.g, clrDim.b, 0.12)
                        visible: logFlick.contentHeight > logFlick.height

                        // Thumb
                        Rectangle {
                            property real ratio:  logFlick.height / Math.max(logFlick.contentHeight, 1)
                            property real thumbH: Math.max(24, ratio * parent.height)
                            property real travel: logFlick.contentHeight - logFlick.height

                            x: 0
                            width: parent.width
                            height: thumbH
                            radius: 3
                            y: travel > 0
                               ? (logFlick.contentY / travel) * (parent.height - thumbH)
                               : 0
                            color: Qt.rgba(clrDim.r, clrDim.g, clrDim.b, 0.7)
                        }
                    }
                }
            }
        }
    }

    Connections {
        target: bridge
        function onLogAppended(message) {
            logArea.append(message)
        }
    }
}
