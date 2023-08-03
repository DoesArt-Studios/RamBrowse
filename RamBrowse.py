from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtWebEngineWidgets import *
from PySide6.QtPrintSupport import *
from PySide6.QtMultimedia import *
from PySide6.QtWebEngineCore import *
from PySide6.QtNetwork import *

import os
import sys

BASE_DIR = os.path.dirname(__file__)

class AboutDialog(QDialog):
    def __init__(self, *args, **kwargs):
        super(AboutDialog, self).__init__(*args, **kwargs)


        self.setStyleSheet("""
            QDialog {
                background-color: #333;
                color: white;
            }
        """)

        QBtn = QDialogButtonBox.Ok  # No cancel
        self.buttonBox = QDialogButtonBox(QBtn)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()

        title = QLabel("RamBrowse")
        font = title.font()
        font.setPointSize(20)
        title.setFont(font)
        title.setAlignment(Qt.AlignHCenter)  # Center the title horizontally

        layout.addWidget(title)

        logo = QLabel()
        logo.setPixmap(QPixmap(os.path.join('images', 'Logo.png')))
        layout.addWidget(logo)

        layout.addWidget(QLabel("Version 2.0.0"))
        layout.addWidget(QLabel("Copyright 2023 DoesArt Studios"))

        layout.addWidget(self.buttonBox)

        self.setLayout(layout)

class DownloadItem(QWebEngineDownloadRequest):
    def __init__(self, download_item, *args, **kwargs):
        super(DownloadItem, self).__init__(*args, **kwargs)
        self.download_item = download_item
        self.download_progress_signal = Signal(int, int)

    def update_progress(self, bytes_received, bytes_total):
        self.download_progress_signal.emit(bytes_received, bytes_total)

    def download_finished(self):
        self.download_progress_signal.emit(0, 1)  # Emit the signal to set progress to 100%

class DownloadDialog(QDialog):
    downloadProgressSignal = Signal(int, int)
    def __init__(self, download_item, *args, **kwargs):
        super(DownloadDialog, self).__init__(*args, **kwargs)
        self.setWindowTitle("Download")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.download_item = download_item

        layout = QVBoxLayout()

        filename_label = QLabel("File Name:")
        self.filename_edit = QLineEdit(download_item.suggestedFileName() if download_item else "")
        layout.addWidget(filename_label)
        layout.addWidget(self.filename_edit)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.download_btn = QPushButton("Download")
        self.download_btn.clicked.connect(self.download)
        self.download_btn.setEnabled(download_item is not None)
        layout.addWidget(self.download_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.cancel)
        layout.addWidget(self.cancel_btn)

        self.setLayout(layout)

        if download_item:
            download_item.downloadProgress.connect(self.update_progress)
            download_item.finished.connect(self.download_finished)

    def update_progress(self, bytes_received, bytes_total):
        if bytes_total > 0:
            self.progress_bar.setMaximum(bytes_total)
            self.progress_bar.setValue(bytes_received)

    def download_finished(self):
        self.close()

    def download(self):
        filename, _ = QInputDialog.getText(self, "Save File", "Enter file name:", QLineEdit.Normal, self.download_item.suggestedFileName())
        if filename:
            # Set the suggested file name for the download
            self.download_item.setDownloadFileName(filename)
            self.download_item.accept()

    def cancel(self):
        self.download_item.cancel()
        self.close()

class Tab(QWebEngineView):
    titleChanged = Signal(str)
    windowTitleChanged = Signal(str)

    def __init__(self, url=None):
        super(Tab, self).__init__()
        self.current_title = ""
        self.history = []
        self.history_index = -1  # Index to track current position in the history
        self.media_player = None  # Initialize media player as None
        self.urlbar = QLineEdit()  # Add the urlbar attribute

        # Create a single instance of the DownloadDialog to be reused for downloads
        self.download_dialog = DownloadDialog(None, self)
        self.download_dialog.downloadProgressSignal.connect(self.update_download_progress)
        self.download_dialog.finished.connect(self.download_finished)

        if url:
            self.setUrl(url)

        self.urlChanged.connect(self.update_urlbar)
        self.loadFinished.connect(self.update_title)

        # Connect the downloadRequested signal to the handle_download_requested method
        self.page().profile().downloadRequested.connect(self.handle_download_requested)

    def update_title(self):
        title = self.page().title()
        if title != self.current_title:
            self.current_title = title
            self.titleChanged.emit(title)
            self.windowTitleChanged.emit(f"{title} - RamBrowse")

    def update_urlbar(self, q):
        self.urlbar.setText(q.toString())
        self.urlbar.setCursorPosition(0)
        self.titleChanged.emit(self.page().title())

    def create_media_player(self):
        if not self.media_player:
            self.media_player = QMediaPlayer(self)  # Create media player instance
            self.media_player.setVideoOutput(self)  # Set video output to the view itself
            self.media_player.stateChanged.connect(self.on_media_state_changed)

    def release_media_player(self):
        if self.media_player:
            self.media_player.stop()  # Stop media playback
            self.media_player.setVideoOutput(None)  # Release video output
            self.media_player.deleteLater()  # Delete the media player instance
            self.media_player = None

    def on_media_state_changed(self, state):
        if state == QMediaPlayer.StoppedState:
            self.release_media_player()

    def changeEvent(self, event):
        if event.type() == QEvent.ActivationChange:
            if not self.isActiveWindow() and self.media_player and self.media_player.state() == QMediaPlayer.PlayingState:
                self.media_player.pause()  # Pause video playback when tab becomes inactive
        super(Tab, self).changeEvent(event)

    def createWebEngineProfile(self):
        profile = QWebEngineProfile(self)
        profile.downloadRequested.connect(self.on_download_requested)
        return profile


    def handle_download_requested(self, download_item):
        if download_item is not None:
            self.download_dialog.download_item = download_item
            self.download_dialog.filename_edit.setText(download_item.suggestedFileName())
            self.download_dialog.download_btn.setEnabled(True)  # Enable the download button
            self.download_dialog.exec_()

    def update_download_progress(self, bytes_received, bytes_total):
        if self.download_dialog.isVisible():
            # If the download dialog is open, update the progress
            self.download_dialog.progress_bar.setMaximum(bytes_total)
            self.download_dialog.progress_bar.setValue(bytes_received)

    def download_finished(self):
        # Reset the download dialog after the download is finished
        self.download_dialog.progress_bar.setValue(0)
        self.download_dialog.progress_bar.setMaximum(100)

    def navigate(self, qurl):
        if self.url() != qurl:
            self.setUrl(qurl)

    def navigate_back(self):
        if self.history_index > 0:
            self.history_index -= 1
            self.navigate(self.history[self.history_index])

    def navigate_forward(self):
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self.navigate(self.history[self.history_index])

    def setUrl(self, qurl):
        super(Tab, self).setUrl(qurl)
        self.update_history(qurl)

    def update_history(self, qurl):
        # Remove all entries after the current index if the user navigated back and then navigated to a new URL
        if self.history_index + 1 < len(self.history):
            self.history = self.history[:self.history_index + 1]

        # Add the new URL to history if it's not the same as the current one
        if not self.history or self.history[-1] != qurl:
            self.history.append(qurl)
            self.history_index = len(self.history) - 1



    def contextMenuEvent(self, event):
        # Create a new context menu
        context_menu = QMenu(self)

        # Add actions to the context menu
        back_action = QAction("Back", self)
        back_action.triggered.connect(self.back)
        context_menu.addAction(back_action)

        forward_action = QAction("Forward", self)
        forward_action.triggered.connect(self.forward)
        context_menu.addAction(forward_action)

        reload_action = QAction("Reload", self)
        reload_action.triggered.connect(self.reload)
        context_menu.addAction(reload_action)

        stop_action = QAction("Stop", self)
        stop_action.triggered.connect(self.stop)
        context_menu.addAction(stop_action)

        # Get the bookmarked URLs and create actions for each bookmark
        bookmarks = self.parent().parent().bookmarks
        if bookmarks:
            bookmark_menu = context_menu.addMenu("Bookmarks")
            for url, title in bookmarks.items():
                bookmark_action = QAction(title, self)
                bookmark_action.setData(url)
                bookmark_action.triggered.connect(self.navigate_to_bookmark)
                bookmark_menu.addAction(bookmark_action)

        # Calculate the position to show the context menu
        event_pos = event.pos()
        event_global_pos = event.globalPos()
        context_menu_height = context_menu.sizeHint().height()
        context_menu_width = context_menu.sizeHint().width()
        available_screens = QGuiApplication.screens()
        screen_rect = available_screens[0].availableGeometry() if available_screens else QRect()

        x = min(event_global_pos.x(), screen_rect.right() - context_menu_width)
        y = min(event_global_pos.y(), screen_rect.bottom() - context_menu_height)

        # Adjust the x position to show the menu on the left side
        if x == event_global_pos.x():
            x = max(event_global_pos.x() - context_menu_width, screen_rect.left())

        # Adjust the y position to show the submenu above or below the main context menu
        available_height = screen_rect.bottom() - y
        if bookmark_menu and context_menu_height < available_height:
            bookmark_menu.exec_(QPoint(x, y + context_menu_height))
        else:
            context_menu.exec_(QPoint(x, y))



class ClosedTabManager:
    def __init__(self, main_window):
        self.main_window = main_window
        self.closed_tabs = []

    def add_closed_tab(self, tab):
        self.closed_tabs.append(tab)

    def reopen_last_closed_tab(self):
        if self.closed_tabs:
            tab_data = self.closed_tabs.pop()
            tab = Tab(tab_data['url'])
            tab.setPage(tab_data['page'])
            self.main_window.tabs.addTab(tab, tab_data['label'])
            self.main_window.tabs.setCurrentWidget(tab)
class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.download_items = {}

        self.closed_tab_manager = ClosedTabManager(self)

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.current_tab = None  # Initialize the current_tab attribute
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)

        self.setCentralWidget(self.tabs)

        navtb = QToolBar("Navigation")
        navtb.setObjectName("NavigationToolbar")  # Set the object name for the navigation toolbar
        self.addToolBar(navtb)
        navtb.setMovable(False)


        back_btn = QAction(QIcon(resource_path('images/arrow-180.png')), "Back", self)
        back_btn.setStatusTip("Back to previous page")
        back_btn.triggered.connect(lambda: self.tabs.currentWidget().back())
        navtb.addAction(back_btn)

        next_btn = QAction(QIcon(resource_path('images/arrow-000.png')), "Forward", self)
        next_btn.setStatusTip("Forward to next page")
        next_btn.triggered.connect(lambda: self.tabs.currentWidget().forward())
        navtb.addAction(next_btn)

        reload_btn = QAction(QIcon(resource_path('images/arrow-circle-315.png')), "Reload", self)
        reload_btn.setStatusTip("Reload page")
        reload_btn.triggered.connect(lambda: self.tabs.currentWidget().reload())
        navtb.addAction(reload_btn)

        home_btn = QAction(QIcon(resource_path('images/home.png')), "Home", self)
        home_btn.setStatusTip("Go home")
        home_btn.triggered.connect(self.navigate_home)
        navtb.addAction(home_btn)

        navtb.addSeparator()

        self.httpsicon = QLabel()  # Yes, really!
        self.httpsicon.setPixmap(QPixmap(resource_path('images/lock-nossl.png')))
        navtb.addWidget(self.httpsicon)

        self.urlbar = QLineEdit()
        self.urlbar.returnPressed.connect(self.navigate_to_url)
        navtb.addWidget(self.urlbar)

        stop_btn = QAction(QIcon(resource_path('images/cross-circle.png')), "Stop", self)
        stop_btn.setStatusTip("Stop loading current page")
        stop_btn.triggered.connect(lambda: self.tabs.currentWidget().stop())
        navtb.addAction(stop_btn)

        file_menu = self.menuBar().addMenu("&File")

        new_tab_action = QAction(QIcon(resource_path('images/ui-tab--plus.png')), "New Tab", self)
        new_tab_action.setStatusTip("Open a new tab")
        new_tab_action.triggered.connect(self.add_new_tab)
        new_tab_action.setShortcut(QKeySequence.AddTab)
        file_menu.addAction(new_tab_action)

        reopen_tab_action = QAction("Reopen Closed Tab", self)
        reopen_tab_action.setStatusTip("Reopen the last closed tab")
        reopen_tab_action.triggered.connect(self.closed_tab_manager.reopen_last_closed_tab)
        reopen_tab_action.setShortcut(QKeySequence("Ctrl+Shift+T"))
        file_menu.addAction(reopen_tab_action)

        self.shortcut_close = QShortcut(QKeySequence('Ctrl+W'), self)
        self.shortcut_close.activated.connect(self.close_current_tab)

        open_file_action = QAction(QIcon(resource_path('images/disk--arrow.png')), "Open file...", self)
        open_file_action.setStatusTip("Open from file")
        open_file_action.triggered.connect(self.open_file)
        file_menu.addAction(open_file_action)

        save_file_action = QAction(QIcon(resource_path('images/disk--pencil.png')), "Save Page As...", self)
        save_file_action.setStatusTip("Save current page to file")
        save_file_action.triggered.connect(self.save_file)
        file_menu.addAction(save_file_action)

        print_action = QAction(QIcon(resource_path('images/printer.png')), "Print...", self)
        print_action.setStatusTip("Print current page")
        print_action.triggered.connect(self.print_page)
        file_menu.addAction(print_action)

        help_menu = self.menuBar().addMenu("&Help")

        about_action = QAction(QIcon(resource_path('images/question.png')), "About RamBrowse", self)
        about_action.setStatusTip("Find out more about RamBrowse")
        about_action.triggered.connect(self.about)
        help_menu.addAction(about_action)

        navigate_rambrowse_action = QAction(QIcon(resource_path('images/lifebuoy.png')),
                                            "RamBrowse Homepage", self)
        navigate_rambrowse_action.setStatusTip("Go to the RamBrowse Homepage")
        navigate_rambrowse_action.triggered.connect(self.navigate_rambrowse)
        help_menu.addAction(navigate_rambrowse_action)

        self.add_new_tab(QUrl('http://duckduckgo.com'), 'Homepage')

        self.show()

        # Keep a reference to the QWebEngineSettings object
        self.web_engine_settings = self.tabs.currentWidget().page().settings()

        # Add the buttons to the toolbar
        navtb.addAction(back_btn)
        navtb.addAction(next_btn)
        navtb.addAction(reload_btn)
        navtb.addAction(home_btn)
        navtb.addSeparator()
        navtb.addWidget(self.httpsicon)
        navtb.addWidget(self.urlbar)
        navtb.addAction(stop_btn)

        self.addToolBar(navtb)  # Add the custom toolbar to the main window

        self.setWindowTitle("RamBrowse")
        self.setWindowIcon(QIcon(resource_path('images/Logo.png')))

        # Add Downloads menu and download manager
        self.download_menu = self.menuBar().addMenu("&Downloads")
        self.download_manager = QNetworkAccessManager(self)
        self.download_manager.finished.connect(self.download_finished)

        # Create a single instance of the DownloadDialog to be reused for downloads
        self.download_dialog = DownloadDialog(None, self)
        # Connect the custom signal to the update_download_progress method in MainWindow
        self.download_dialog.downloadProgressSignal.connect(self.update_download_progress)
        self.download_dialog.finished.connect(self.download_finished)

        # Handle download requests within the tab
        profile = QWebEngineProfile.defaultProfile()
        profile.downloadRequested.connect(self.on_download_requested)

        # Add tooltips to toolbar buttons
        back_btn.setToolTip("Go Back (Alt+Left)")
        next_btn.setToolTip("Go Forward (Alt+Right)")
        reload_btn.setToolTip("Reload Page (Ctrl+R)")
        home_btn.setToolTip("Go Home (Alt+Home)")
        stop_btn.setToolTip("Stop Loading (Esc)")

        # Add status bar messages
        back_btn.setStatusTip("Go back to the previous page")
        next_btn.setStatusTip("Go forward to the next page")
        reload_btn.setStatusTip("Reload the current page")
        home_btn.setStatusTip("Go to the homepage")
        stop_btn.setStatusTip("Stop loading the current page")

        # Add the "Bookmark" action to the toolbar
        self.bookmark_action = QAction(QIcon(resource_path('images/bookmark.png')), "Bookmark", self)
        self.bookmark_action.triggered.connect(self.add_bookmark)
        navtb.insertAction(navtb.actions()[0], self.bookmark_action)  # Insert the bookmark action at the beginning
        navtb.addAction(self.bookmark_action)

        # Create a Bookmarks menu
        self.bookmark_counter = 0
        self.bookmarks_menu = QMenu("Bookmarks", self)
        navtb.addWidget(self.bookmarks_menu)

        self.update_bookmark_counter()  # Call the function to initialize the bookmark counter label

        # Initialize a dictionary to store the bookmarks
        self.bookmarks = {}
        # Add separator and bookmark button to the toolbar
        navtb.addSeparator()
        navtb.addAction(self.bookmark_action)
        navtb.addWidget(self.bookmarks_menu)

        self.addToolBar(navtb)

    def add_bookmark(self):
        current_tab = self.tabs.currentWidget()
        current_url = current_tab.url().toString()
        current_title = current_tab.title()

        # Check if the bookmark is already stored
        if current_url in self.bookmarks:
            return

        # Add the bookmark to the bookmarks menu
        bookmark_action = QAction(current_title, self)
        bookmark_action.setData(current_url)
        bookmark_action.triggered.connect(self.navigate_to_bookmark)
        self.bookmarks_menu.addAction(bookmark_action)

        # Store the bookmark in the bookmarks dictionary
        self.bookmarks[current_url] = current_title
        self.bookmark_counter += 1  # Increment the bookmark counter
        self.update_bookmark_counter()  # Update the bookmark counter label

        navtb = self.findChild(QToolBar, "NavigationToolbar")  # Find the navigation toolbar by its object name
        if navtb is not None:
            navtb.insertAction(navtb.actions()[0], self.bookmark_action)  # Insert the bookmark action at the beginning
        else:
            print("Navigation toolbar not found!")
        navtb.insertAction(navtb.actions()[0], self.bookmark_action)  # Insert the bookmark action at the beginning

    def update_bookmark_counter(self):
        self.bookmark_action.setText("Bookmark ({})".format(self.bookmark_counter))

    def navigate_to_bookmark(self):
        action = self.sender()
        if action:
            url = action.data()
            self.tabs.currentWidget().setUrl(QUrl(url))

    def keyPressEvent(self, event):
        # Handle keyboard shortcuts for better user experience
        modifiers = event.modifiers()
        if modifiers == Qt.AltModifier or modifiers == (Qt.AltModifier | Qt.AltModifier):
            if event.key() == Qt.Key_Left:  # Alt+Left for Back
                self.tabs.currentWidget().back()
            elif event.key() == Qt.Key_Right:  # Alt+Right for Forward
                self.tabs.currentWidget().forward()
        elif modifiers == Qt.ControlModifier:
            if event.key() == Qt.Key_R:  # Ctrl+R for Reload
                self.tabs.currentWidget().reload()


        super(MainWindow, self).keyPressEvent(event)

    def add_new_tab(self, qurl=None, label="Blank"):
        tab = Tab(qurl)

        if qurl is None:
            qurl = QUrl('https://duckduckgo.com/')

        browser = QWebEngineView()
        browser.setUrl(qurl)
        i = self.tabs.addTab(browser, label)

        self.tabs.setCurrentIndex(i)

        browser.urlChanged.connect(lambda qurl, browser=browser:
                                   self.update_urlbar(qurl, browser))
        browser.loadFinished.connect(lambda _, i=i, browser=browser:
                                     self.tabs.setTabText(i, browser.page().title()))
        browser.titleChanged.connect(lambda title, i=i: self.tabs.setTabText(i, title))
        browser.windowTitleChanged.connect(lambda title: self.setWindowTitle(title))

        # Enable video support in the current tab
        browser.page().featurePermissionRequested.connect(self.handle_feature_permission)
        browser.page().settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)

        # Create a single instance of the DownloadDialog to be reused for downloads
        self.download_dialog = DownloadDialog(None, self)
        # Connect the custom signal to the update_download_progress method in MainWindow
        self.download_dialog.downloadProgressSignal.connect(self.update_download_progress)
        self.download_dialog.finished.connect(self.download_finished)

        # Connect the context menu to the contextMenuEvent method
        browser.setContextMenuPolicy(Qt.CustomContextMenu)
        browser.customContextMenuRequested.connect(self.context_menu_requested)

        # Handle download requests within the tab
        tab.page().profile().downloadRequested.connect(self.on_download_requested)

        # Connect the custom signal to the update_download_progress method in MainWindow
        tab.download_dialog.downloadProgressSignal.connect(self.update_download_progress)
        self.tabs.setCurrentWidget(tab)
        self.current_tab = tab  # Set the current_tab attribute when a new tab is added

    def context_menu_requested(self, pos):
        current_tab = self.tabs.currentWidget()
        hit_test_result = current_tab.hitTest(pos)
        if not hit_test_result.isContentEditable():
            menu = QMenu(self)

            # Add the "Open Link in New Tab" action to the context menu
            link_url = hit_test_result.linkUrl()
            if not link_url.isEmpty():
                open_link_in_new_tab_action = QAction("Open Link in New Tab", self)
                open_link_in_new_tab_action.triggered.connect(lambda: self.add_new_tab(link_url, "Link"))
                menu.addAction(open_link_in_new_tab_action)

            # Add the "Bookmark" action to the context menu
            bookmark_action = QAction("Bookmark", self)
            bookmark_action.triggered.connect(self.add_bookmark)
            menu.addAction(bookmark_action)

            menu.exec_(current_tab.mapToGlobal(pos))

    def on_download_requested(self, download_item):
        if download_item is not None:
            self.download_dialog.download_item = download_item
            self.download_dialog.filename_edit.setText(download_item.suggestedFileName())
            self.download_dialog.download_btn.setEnabled(True)  # Enable the download button
            self.download_dialog.exec_()

    def update_download_progress(self, bytes_received, bytes_total):
        if self.download_dialog.isVisible():
            # If the download dialog is open, update the progress
            self.download_dialog.progress_bar.setMaximum(bytes_total)
            self.download_dialog.progress_bar.setValue(bytes_received)

    def download_finished(self):
        # Reset the download dialog after the download is finished
        self.download_dialog.progress_bar.setValue(0)
        self.download_dialog.progress_bar.setMaximum(100)

    def show_notification(self, title, message):
        notification = QSystemTrayIcon(self)
        notification.setIcon(self.windowIcon())
        notification.showMessage(title, message, QSystemTrayIcon.Information, 5000)
        notification.deleteLater()
    def tab_open_doubleclick(self, i):
        if i == -1:  # No tab under the click
            self.add_new_tab()

    def current_tab_changed(self, i):
        self.current_tab = self.tabs.currentWidget()
        qurl = self.tabs.currentWidget().url()
        self.update_urlbar(qurl, self.tabs.currentWidget())
        self.update_title(self.tabs.currentWidget())



    def close_current_tab(self):
        if self.tabs.count() < 2:
            return

        index = self.tabs.currentIndex()
        tab_widget = self.tabs.widget(index)
        self.closed_tab_manager.add_closed_tab({
            'url': tab_widget.url(),
            'label': self.tabs.tabText(index),
            'page': tab_widget.page()
        })
        self.tabs.removeTab(index)


    def update_title(self, browser):
        if browser != self.tabs.currentWidget():
            # If this signal is not from the current tab, ignore
            return

        title = self.tabs.currentWidget().page().title()
        self.setWindowTitle("%s - RamBrowse" % title)

    def navigate_rambrowse(self):
        self.tabs.currentWidget().setUrl(QUrl("https://DoesArt-Studios.github.io/RamBrowseWebsite"))

    def about(self):
        dlg = AboutDialog()
        dlg.exec_()

    def open_file(self):
        filename, _ = QFileDialog.getOpenFileName(self, "Open file", "",
                                                  "Hypertext Markup Language (*.htm *.html);;"
                                                  "All files (*.*)")

        if filename:
            with open(filename, 'r') as f:
                html = f.read()

            self.tabs.currentWidget().setHtml(html)
            self.urlbar.setText(filename)

    def save_file(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Page As", "",
                                                  "Hypertext Markup Language (*.htm *html);;"
                                                  "All files (*.*)")

        if filename:
            html = self.tabs.currentWidget().page().toHtml()
            with open(filename, 'w') as f:
                f.write(html.encode('utf8'))

    def print_page(self):
        dlg = QPrintPreviewDialog()
        dlg.paintRequested.connect(self.browser.print_)
        dlg.exec_()

    def navigate_back(self):
        if self.current_tab:
            self.current_tab.navigate_back()

    def navigate_forward(self):
        if self.current_tab:
            self.current_tab.navigate_forward()

    def navigate_home(self):
        if self.current_tab:
            self.current_tab.navigate(QUrl("http://duckduckgo.com"))

    def navigate_to_url(self):
        if self.current_tab:
            q = QUrl(self.urlbar.text())
            if q.scheme() == "":
                q.setScheme("http")
            self.current_tab.navigate(q)

    def update_urlbar(self, q, browser=None):
        if browser != self.tabs.currentWidget():
            # If this signal is not from the current tab, ignore
            return

        if q.scheme() == 'https':
            # Secure padlock icon
            self.httpsicon.setPixmap(QPixmap(resource_path('images/lock-ssl.png')))
        else:
            # Insecure padlock icon
            self.httpsicon.setPixmap(QPixmap(resource_path('images/lock-nossl.png')))

        self.urlbar.setText(q.toString())
        self.urlbar.setCursorPosition(0)

    def update_tab_label(self, title):
        current_tab = self.tabs.currentWidget()
        index = self.tabs.indexOf(current_tab)
        self.tabs.setTabText(index, title)

    def closeEvent(self, event):
        # Handle window title when closing the last tab
        if self.tabs.count() == 0:
            self.setWindowTitle("RamBrowse")
        super(MainWindow, self).closeEvent(event)

    def handle_feature_permission(self, url, feature):
        if feature == QWebEnginePage.MediaAudioCapture or feature == QWebEnginePage.MediaVideoCapture:
            self.sender().setFeaturePermission(url, feature, QWebEnginePage.PermissionGrantedByUser)

        # Add the "Dark Mode" action to the toolbar
        self.dark_mode_action = QAction("Dark Mode", self)
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.toggled.connect(self.toggle_dark_mode)
        self.toolbar.addAction(self.dark_mode_action)

    def toggle_dark_mode(self, checked):
        if checked:
            dark_mode_css = """
                body {
                    background-color: #222;
                    color: #fff;
                }
                /* Add other CSS styles for dark mode as needed */
            """
            self.tabs.setStyleSheet(dark_mode_css)
        else:
            self.tabs.setStyleSheet("")


def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        # For PyInstaller executable, return the absolute path based on the _MEIPASS attribute
        base_path = sys._MEIPASS
    else:
        # For regular Python script, return the absolute path based on the current working directory
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)
app = QApplication(sys.argv)
app.setWindowIcon(QIcon(resource_path('logo.ico')))
app.setApplicationName("RamBrowse")
app.setOrganizationName("DoesArt Studios")
app.setOrganizationDomain("https://DoesArt-Studios.gihtub.io/RamBrowseWebsite/")

window = MainWindow()

app.exec()
