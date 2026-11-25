#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QQuickWindow>
#include <QCommandLineParser>
#include <QCommandLineOption>
#include <QIcon>
#include <QFile>
#include <QFileInfo>
#include <QDir>
#include <QStandardPaths>
#include <QtWebEngineQuick/qtwebenginequickglobal.h>
#include <iostream>

static const char *appWindowQml = R"QML(
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtWebEngine

Window {
    id: root
    visible: true
    width: 1100
    height: 750
    minimumWidth: 500
    minimumHeight: 380
    title: appName
    flags: Qt.Window | Qt.FramelessWindowHint
    color: "#181a1f"

    property bool webHeaderHidden: initialHideWebHeader

    WebEngineProfile {
        id: webProfile
        storageName: appSlug
        persistentStoragePath: storageDir
        cachePath: cacheDir
        persistentCookiesPolicy: WebEngineProfile.AllowPersistentCookies
        httpUserAgent: "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }

    // Created Application Bar (Custom Native Header with Window Controls)
    Rectangle {
        id: appHeader
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: 38
        color: "#1e222b"
        z: 100

        Rectangle {
            anchors.bottom: parent.bottom
            anchors.left: parent.left
            anchors.right: parent.right
            height: 1
            color: Qt.rgba(1, 1, 1, 0.08)
        }

        DragHandler {
            target: null
            onActiveChanged: if (active) root.startSystemMove()
        }

        TapHandler {
            gesturePolicy: TapHandler.WithinBounds
            onDoubleTapped: {
                if (root.visibility === Window.Maximized) {
                    root.showNormal()
                } else {
                    root.showMaximized()
                }
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 10
            anchors.rightMargin: 0
            spacing: 8

            // App Icon
            Image {
                id: appIconImg
                source: {
                    if (appIcon.indexOf("/") !== -1) return "file://" + appIcon
                    if (appIcon !== "") return "image://icon/" + appIcon
                    return ""
                }
                Layout.preferredWidth: 20
                Layout.preferredHeight: 20
                fillMode: Image.PreserveAspectFit
                visible: source !== ""
            }

            // App Name
            Label {
                text: root.title
                color: "#f6f8fa"
                font.pixelSize: 13
                font.bold: true
                Layout.alignment: Qt.AlignVCenter
                elide: Text.ElideRight
            }

            // Navigation Controls: Back, Forward, Reload
            RowLayout {
                spacing: 3
                Layout.alignment: Qt.AlignVCenter

                Rectangle {
                    Layout.preferredWidth: 26; Layout.preferredHeight: 26; radius: 5
                    color: backMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                    opacity: webView.canGoBack ? 1.0 : 0.35
                    Text { text: "←"; color: "#ffffff"; font.pixelSize: 14; anchors.centerIn: parent }
                    MouseArea {
                        id: backMouse; anchors.fill: parent; hoverEnabled: true
                        cursorShape: webView.canGoBack ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: if (webView.canGoBack) webView.goBack()
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 26; Layout.preferredHeight: 26; radius: 5
                    color: fwdMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                    opacity: webView.canGoForward ? 1.0 : 0.35
                    Text { text: "→"; color: "#ffffff"; font.pixelSize: 14; anchors.centerIn: parent }
                    MouseArea {
                        id: fwdMouse; anchors.fill: parent; hoverEnabled: true
                        cursorShape: webView.canGoForward ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onClicked: if (webView.canGoForward) webView.goForward()
                    }
                }

                Rectangle {
                    Layout.preferredWidth: 26; Layout.preferredHeight: 26; radius: 5
                    color: reloadMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                    Text { text: webView.loading ? "✕" : "⟳"; color: "#ffffff"; font.pixelSize: 14; anchors.centerIn: parent }
                    MouseArea {
                        id: reloadMouse; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (webView.loading) webView.stop()
                            else webView.reload()
                        }
                    }
                }

                // Web UI Top Bar Visibility Toggle Badge
                Rectangle {
                    Layout.preferredWidth: 84; Layout.preferredHeight: 22; radius: 11
                    color: root.webHeaderHidden ? Qt.rgba(0.2, 0.6, 1.0, 0.22) : (hdrMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : Qt.rgba(1, 1, 1, 0.06))
                    border.color: root.webHeaderHidden ? "#3584e4" : Qt.rgba(1, 1, 1, 0.15)
                    border.width: 1
                    Text {
                        text: root.webHeaderHidden ? "Web Bar: Off" : "Web Bar: On"
                        color: root.webHeaderHidden ? "#64b5f6" : Qt.rgba(1, 1, 1, 0.75)
                        font.pixelSize: 10
                        font.bold: true
                        anchors.centerIn: parent
                    }
                    MouseArea {
                        id: hdrMouse; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.webHeaderHidden = !root.webHeaderHidden
                            webView.applyTopBarVisibility()
                        }
                    }
                }
            }

            // Draggable Spacer Area
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true
            }

            // Window Action Buttons: Minimize, Maximize/Restore, Close
            RowLayout {
                spacing: 0
                Layout.alignment: Qt.AlignRight | Qt.AlignVCenter

                // Minimize
                Rectangle {
                    Layout.preferredWidth: 44; Layout.preferredHeight: 38
                    color: minMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                    Text { text: "—"; color: "#ffffff"; font.pixelSize: 12; anchors.centerIn: parent }
                    MouseArea {
                        id: minMouse; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.showMinimized()
                    }
                }

                // Maximize / Restore
                Rectangle {
                    Layout.preferredWidth: 44; Layout.preferredHeight: 38
                    color: maxMouse.containsMouse ? Qt.rgba(1, 1, 1, 0.12) : "transparent"
                    Text {
                        text: root.visibility === Window.Maximized ? "❐" : "□"
                        color: "#ffffff"
                        font.pixelSize: 12
                        anchors.centerIn: parent
                    }
                    MouseArea {
                        id: maxMouse; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            if (root.visibility === Window.Maximized) root.showNormal()
                            else root.showMaximized()
                        }
                    }
                }

                // Close
                Rectangle {
                    Layout.preferredWidth: 46; Layout.preferredHeight: 38
                    color: closeMouse.containsMouse ? "#e81123" : "transparent"
                    Text { text: "✕"; color: "#ffffff"; font.pixelSize: 13; anchors.centerIn: parent }
                    MouseArea {
                        id: closeMouse; anchors.fill: parent; hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.close()
                    }
                }
            }
        }
    }

    // Embedded Web Application View
    WebEngineView {
        id: webView
        anchors.top: appHeader.bottom
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        profile: webProfile
        url: appUrl

        settings.javascriptEnabled: true
        settings.pluginsEnabled: true
        settings.fullScreenSupportEnabled: true
        settings.localContentCanAccessRemoteUrls: true

        function applyTopBarVisibility() {
            var css = "#gb, header#gb, .gb_Fd, #masthead-container, #masthead, ytd-masthead, ytmusic-nav-bar, div[role='banner'], header[role='banner'] { display: none !important; } body, html { margin-top: 0 !important; padding-top: 0 !important; } #content, #page-manager, ytd-app { margin-top: 0 !important; padding-top: 0 !important; }";
            var js = "(function() { var sid = '__googleapp_topbar_style__'; var el = document.getElementById(sid); if (" + (root.webHeaderHidden ? "true" : "false") + ") { if (!el) { el = document.createElement('style'); el.id = sid; el.textContent = " + JSON.stringify(css) + "; document.head.appendChild(el); } } else { if (el) el.remove(); } })();";
            webView.runJavaScript(js);
        }

        onLoadingChanged: function(loadRequest) {
            if (loadRequest.status === WebEngineView.LoadSucceededStatus) {
                applyTopBarVisibility();
            }
        }

        onPermissionRequested: function(request) {
            request.grant();
        }

        onFullScreenRequested: function(request) {
            if (request.toggleOn) {
                root.showFullScreen();
            } else {
                root.showNormal();
            }
            request.accept();
        }
    }

    // Window Edge Resize Handlers (Borders & Corners)
    MouseArea {
        anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom; width: 6; z: 200
        cursorShape: Qt.SizeHorCursor
        onPressed: root.startSystemResize(Qt.LeftEdge)
    }
    MouseArea {
        anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom; width: 6; z: 200
        cursorShape: Qt.SizeHorCursor
        onPressed: root.startSystemResize(Qt.RightEdge)
    }
    MouseArea {
        anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; height: 6; z: 200
        cursorShape: Qt.SizeVerCursor
        onPressed: root.startSystemResize(Qt.TopEdge)
    }
    MouseArea {
        anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right; height: 6; z: 200
        cursorShape: Qt.SizeVerCursor
        onPressed: root.startSystemResize(Qt.BottomEdge)
    }

    // Corner Resize Handlers
    MouseArea {
        anchors.top: parent.top; anchors.left: parent.left; width: 12; height: 12; z: 201
        cursorShape: Qt.SizeFDiagCursor
        onPressed: root.startSystemResize(Qt.TopEdge | Qt.LeftEdge)
    }
    MouseArea {
        anchors.top: parent.top; anchors.right: parent.right; width: 12; height: 12; z: 201
        cursorShape: Qt.SizeBDiagCursor
        onPressed: root.startSystemResize(Qt.TopEdge | Qt.RightEdge)
    }
    MouseArea {
        anchors.bottom: parent.bottom; anchors.left: parent.left; width: 12; height: 12; z: 201
        cursorShape: Qt.SizeBDiagCursor
        onPressed: root.startSystemResize(Qt.BottomEdge | Qt.LeftEdge)
    }
    MouseArea {
        anchors.bottom: parent.bottom; anchors.right: parent.right; width: 12; height: 12; z: 201
        cursorShape: Qt.SizeFDiagCursor
        onPressed: root.startSystemResize(Qt.BottomEdge | Qt.RightEdge)
    }

    // Global Shortcuts
    Shortcut { sequence: "F11"; onActivated: root.visibility = (root.visibility === Window.FullScreen ? Window.Windowed : Window.FullScreen) }
    Shortcut { sequence: "F5"; onActivated: webView.reload() }
    Shortcut { sequence: "Ctrl+R"; onActivated: webView.reload() }
    Shortcut { sequence: "Alt+Left"; onActivated: if (webView.canGoBack) webView.goBack() }
    Shortcut { sequence: "Alt+Right"; onActivated: if (webView.canGoForward) webView.goForward() }
    Shortcut { sequence: "Ctrl+H"; onActivated: { root.webHeaderHidden = !root.webHeaderHidden; webView.applyTopBarVisibility(); } }
    Shortcut { sequence: "Ctrl+Q"; onActivated: root.close() }
}
)QML";

int main(int argc, char *argv[]) {
    qputenv("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox");
    QtWebEngineQuick::initialize();

    QGuiApplication app(argc, argv);

    QCommandLineParser parser;
    parser.setApplicationDescription("GoogleApp Standalone Web App Runner");
    parser.addHelpOption();

    QCommandLineOption slugOpt("slug", "Application slug identifier", "slug", "web-app");
    QCommandLineOption nameOpt("name", "Application display name", "name", "Web App");
    QCommandLineOption urlOpt("url", "Application web URL", "url", "https://google.com");
    QCommandLineOption iconOpt("icon", "Application icon file or name", "icon", "");
    QCommandLineOption showHeaderOpt("show-web-header", "Keep the web UI top bar visible by default");

    parser.addOption(slugOpt);
    parser.addOption(nameOpt);
    parser.addOption(urlOpt);
    parser.addOption(iconOpt);
    parser.addOption(showHeaderOpt);

    parser.process(app);

    QString slug = parser.value(slugOpt);
    QString name = parser.value(nameOpt);
    QString url = parser.value(urlOpt);
    QString icon = parser.value(iconOpt);
    bool hideWebHeader = !parser.isSet(showHeaderOpt);

    QString desktopId = QString("googleapp-%1").arg(slug);
    app.setDesktopFileName(desktopId);
    app.setApplicationName(name);

    if (!icon.isEmpty() && QFile::exists(icon)) {
        app.setWindowIcon(QIcon(icon));
    }

    QString dataDir = QStandardPaths::writableLocation(QStandardPaths::AppDataLocation);
    if (dataDir.isEmpty()) {
        dataDir = QDir::homePath() + "/.local/share/googleapp";
    }
    QString storageDir = QString("%1/profiles/%2").arg(dataDir, desktopId);
    QString cacheDir = QString("%1/.cache/googleapp/%2").arg(QDir::homePath(), desktopId);

    QDir().mkpath(storageDir);
    QDir().mkpath(cacheDir);

    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("appSlug", slug);
    engine.rootContext()->setContextProperty("appName", name);
    engine.rootContext()->setContextProperty("appUrl", url);
    engine.rootContext()->setContextProperty("appIcon", icon);
    engine.rootContext()->setContextProperty("initialHideWebHeader", hideWebHeader);
    engine.rootContext()->setContextProperty("storageDir", storageDir);
    engine.rootContext()->setContextProperty("cacheDir", cacheDir);

    engine.loadData(QByteArray(appWindowQml));
    if (engine.rootObjects().isEmpty()) {
        std::cerr << "Failed to load GoogleApp window QML" << std::endl;
        return -1;
    }

    return app.exec();
}
