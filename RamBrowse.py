from PySide6.QtCore import *
from PySide6.QtWidgets import *
from PySide6.QtGui import *
from PySide6.QtWebEngineWidgets import *
from PySide6.QtPrintSupport import *
from PySide6.QtMultimedia import *
from PySide6.QtWebEngineCore import *
from PySide6.QtNetwork import *


import platform
import requests
import os
import sys
import tqdm

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

class TabWidget(QTabWidget):
    def __init__(self):
        super().__init__()

    def add_new_tab(self, browser, label):
        i = self.addTab(browser, label)
        browser.title_changed_connection = browser.titleChanged.connect(self.update_tab_title)
        return i

class WebBrowserTab(QWebEngineView):
    titleChanged = Signal(str)

    def __init__(self, url, label):
        super().__init__()

        self.download_progress_bar = QProgressBar()  # Create a progress bar
        self.download_progress_bar.hide()  # Initially hide the progress bar
        self.download_progress_bar.setMaximum(100)  # Set the maximum value

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.download_progress_bar)
        self.layout.addWidget(self)

        self.setLayout(self.layout)

        self.page().urlChanged.connect(self.update_url)
        self.load(url)

        self.label = label

    def download_requested(self, download_item):
        save_path = os.path.join(self.parent().download_path, download_item.suggestedFileName())
        self.download_file(download_item.url().toString(), save_path, 'application/octet-stream')

    def download_file(self, url, save_path, mime_type):
        headers = {'Accept': mime_type}
        response = requests.get(url, headers=headers, stream=True)
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            chunk_size = 1024
            downloaded = 0

            with open(save_path, 'wb') as file:
                for data in response.iter_content(chunk_size=chunk_size):
                    downloaded += len(data)
                    file.write(data)
                    progress = int((downloaded / total_size) * 100)
                    self.download_progress_bar.setValue(progress)  # Update the progress bar

            print("Download complete")
            self.download_progress_bar.hide()  # Hide the progress bar when download is complete

    def update_url(self, q):
        self.url = q
        self.titleChanged.emit(self.label)  # Emit the signal with the stored label



class TitleChangedSignal(QObject):
    changed = Signal(str)

class Tab(QWebEngineView):
    TitleChangedSignal = Signal(str)
    titleChanged = Signal(str)
    windowTitleChanged = Signal(str)

    def __init__(self, parent=None, url=None):
        super(Tab, self).__init__()
        self.current_title = ""
        self.parent_window = parent  # Store a reference to the parent MainWindow
        self.history = []
        self.history_index = -1  # Index to track current position in the history
        self.media_player = None  # Initialize media player as None
        self.urlbar = QLineEdit()  # Add the urlbar attribute

        self.webpage = QWebEnginePage(self)
        self.setPage(self.webpage)
        
        self.webpage.titleChanged.connect(self.update_tab_label)
        self.webpage.urlChanged.connect(self.update_urlbar)





        self.title_changed_signal = TitleChangedSignal()  # Custom signal for title change # Create a custom signal
        self.title_changed_signal.changed.connect(self.update_tab_label)  # Connect custom signal

        if url:
            self.setUrl(url)
        else:
            self.setUrl(QUrl('http://duckduckgo.com'))

        self.page().titleChanged.connect(self.update_tab_label)  # Connect titleChanged signal
        if url:
            self.setUrl(url)
        self.urlChanged.connect(self.update_urlbar)

        self.tab_index = None  # Add a variable to keep track of the tab's index in the QTabWidget

        # Connect the loadFinished signal to the update_title method
        self.loadFinished.connect(self.update_title)


    def closeEvent(self, event):
        # Disconnect the titleChanged signal when the tab is closed
        self.title_changed_signal.changed.disconnect(self.update_tab_label)
        super(Tab, self).closeEvent(event)


    def update_tab_label(self, title):
        self.TitleChangedSignal.emit(title)  # Emit the title changed signal



    def titleChanged(self, title):
        self.title_changed_signal.changed.emit(title)  # Emit custom signal with the new title



    def update_title(self):
        title = self.page().title()
        print("Title Changed:", title)
        if title != self.current_title:
            self.current_title = title
            self.titleChanged.emit(title)  # Emit the signal
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
        # Set the Permissions-Policy header to exclude unrecognized features
        headers = profile.httpUserAgentProfile().httpSettings().requestHeaders()
        if 'Permissions-Policy' in headers:
            policy_header = headers['Permissions-Policy']
            policy_header = policy_header.replace('unload', '').replace('ch-ua-form-factor', '')
            policy_header = policy_header.replace('interest-cohort', '')  # Remove interest-cohort
            headers['Permissions-Policy'] = policy_header
        else:
            headers['Permissions-Policy'] = ''
        profile.httpUserAgentProfile().httpSettings().setRequestHeaders(headers)

        # Rest of the method remains the same
        profile.settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.JavascriptCanOpenWindows, True)
        profile.settings().setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        profile.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)

        return profile

    def close_current_tab(self, index):
        if self.tabs.count() < 2:
            return
        removed_tab = self.tabs.widget(index)  # Store the removed tab

        # Close the tab, which will trigger the closeEvent and disconnect the signal
        removed_tab.close()


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
        else:
            return

class MainWindow(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)

        self.download_items = {}

        self.closed_tab_manager = ClosedTabManager(self)

        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)



        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.tab_open_doubleclick)
        self.current_tab = None  # Initialize the current_tab attribute
        self.tabs.currentChanged.connect(self.current_tab_changed)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_current_tab)
        self.tabs.currentChanged.connect(self.tab_changed)
        self.setCentralWidget(self.tabs)
        # Initialize the current_tab_index attribute to None
        self.current_tab_index = None

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
        self.shortcut_close.activated.connect(self.close_current_tab_shortcut)

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


        self.download_path = os.path.expanduser("~") + "/Downloads/"
        if platform.system() == "Windows":
            self.download_path = os.path.expanduser("~") + "\\Downloads\\"

        self.browser.page().profile().downloadRequested.connect(self.download_requested)

        self.show()



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

        self.bookmarks = {}  # Initialize the bookmarks attribute as an empty dictionary


        self.bookmarks_toolbar = self.addToolBar("Bookmarks")
        self.bookmarks_toolbar.setObjectName("BookmarksToolbar")
        self.add_bookmark_action = QAction(QIcon(resource_path('images/bookmark.png')), "Add Bookmark", self)
        self.add_bookmark_action.triggered.connect(self.add_bookmark)
        self.bookmarks_toolbar.addAction(self.add_bookmark_action)


        self.addToolBar(navtb)



    def createWebEngineProfile(self):
        profile = QWebEngineProfile(self)

        # Get the default content security policy of the profile
        default_csp = profile.contentSettings().contentSecurityPolicy()

        # Get the existing Permissions-Policy header (if set)
        permissions_policy = default_csp.policy(QWebEngineSettings.PermissionsPolicy)

        # Remove the 'unload' and 'ch-ua-form-factor' features, if present
        if permissions_policy:
            permissions_policy = permissions_policy.replace("unload=(),", "").replace("ch-ua-form-factor=(),", "")

        # Set the updated Permissions-Policy header
        default_csp.setPolicy(QWebEngineSettings.PermissionsPolicy, permissions_policy)

        return profile

    def add_bookmark(self):
        current_tab = self.tabs.currentWidget()
        current_url = current_tab.url().toString()
        current_title = current_tab.title()

        if current_url not in self.bookmarks:
            bookmark_action = QAction(current_title, self)
            bookmark_action.setData(current_url)
            bookmark_action.triggered.connect(self.navigate_to_bookmark)
            self.bookmarks_toolbar.addAction(bookmark_action)
            self.bookmarks[current_url] = current_title
            self.update_bookmark_counter()

    def navigate_to_bookmark(self):
        action = self.sender()
        if action:
            url = action.data()
            self.tabs.currentWidget().setUrl(QUrl(url))


    def update_bookmarks_toolbar(self):
        self.bookmarks_toolbar.clear()  # Clear existing actions in the toolbar
        self.bookmarks_toolbar.addAction(self.add_bookmark_action)  # Re-add the add bookmark action
        for url, title in self.bookmarks.items():
            bookmark_action = QAction(title, self)
            bookmark_action.setData(url)
            bookmark_action.triggered.connect(self.navigate_to_bookmark)
            self.bookmarks_toolbar.addAction(bookmark_action)

    def update_bookmark_counter(self):
        self.add_bookmark_action.setText("Add Bookmark ({})".format(len(self.bookmarks)))


    def keyPressEvent(self, event):
        # Handle keyboard shortcuts for better user experience
        modifiers = event.modifiers()
        if event.key() == Qt.Key_W and event.modifiers() == Qt.ControlModifier:
            current_index = self.tabs.currentIndex()
            if current_index >= 0:
                self.close_current_tab(current_index)
            print("Ctrl+W pressed")  # Add this line


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
        tab.title_changed_signal.changed.connect(self.update_tab_title)

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
        # Connect the titleChanged signal to update_tab_label with a lambda function
        browser.titleChanged.connect(lambda title: self.update_tab_title(title))
        browser.windowTitleChanged.connect(lambda title: self.setWindowTitle(title))

        # Enable video support in the current tab
        browser.page().featurePermissionRequested.connect(self.handle_feature_permission)
        browser.page().settings().setAttribute(QWebEngineSettings.JavascriptEnabled, True)





        self.tabs.setCurrentWidget(tab)
        self.current_tab = tab  # Set the current_tab attribute when a new tab is added

    def get_current_tab(self):
        """
        Returns the currently active tab (QWebEngineView instance).
        """
        return self.tabs.currentWidget()

    def tab_changed(self, index):
        self.current_tab_index = index

        if self.current_tab_index is not None:
            previous_tab = self.tabs.widget(self.current_tab_index)
            if hasattr(previous_tab, 'title_changed_connection'):
                previous_tab.titleChanged.disconnect(previous_tab.title_changed_connection)

        current_tab = self.tabs.currentWidget()
        current_tab.title_changed_connection = current_tab.titleChanged.connect(self.update_tab_title)

    def download_requested(self, download_item):
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.AnyFile)
        save_path, _ = file_dialog.getSaveFileName(
            self,
            "Save File",
            os.path.join(self.download_path, download_item.suggestedFileName()),
            "All Files (*)",
            options=options,
        )

        if save_path:
            self.download_file(download_item.url().toString(), save_path)

    def download_file(self, url, save_path):
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            total_size = int(response.headers.get('content-length', 0))
            chunk_size = 1024
            with open(save_path, 'wb') as file:
                for data in response.iter_content(chunk_size=chunk_size):
                    file.write(data)
            print("Download complete.")


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

    def close_current_tab(self, index):
        if self.tabs.count() < 2:
            return
        if index is None:  # No tab index provided, use current
            index = self.tabs.currentIndex()

        widget = self.tabs.widget(index)
        if widget is not None:

            removed_tab = self.tabs.widget(index)

        # Check if the removed_tab is not None before disconnecting the signal
        if removed_tab is not None:
            removed_tab.titleChanged.disconnect(self.update_tab_title)

        self.closed_tab_manager.add_closed_tab({
            'url': removed_tab.url() if removed_tab else None,
            'label': self.tabs.tabText(index) if removed_tab else None,
            'page': removed_tab.page() if removed_tab else None
        })

        self.tabs.removeTab(index)

        # Update current_tab
        self.current_tab = self.tabs.currentWidget()
        if self.current_tab:
            # Reconnect the signal to the method in the current active tab
            self.current_tab.titleChanged.connect(self.update_tab_title)

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


    def navigate_back(self):
        if self.current_tab:
            self.current_tab.navigate_back()

    def navigate_forward(self):
        if self.current_tab:
            self.current_tab.navigate_forward()

    def navigate_home(self):
        self.current_tab.setUrl(QUrl("http://duckduckgo.com/"))

    def navigate_to_url(self):
        input_text = self.urlbar.text()
        if input_text:
           # Check if the input is a valid URL
            q = QUrl(input_text)
            if q.scheme() == "":
                # If it's not a valid URL, treat it as a search query
                search_query = input_text.replace(" ", "+")  # Replace spaces with '+' for URL
                search_url = QUrl("https://duckduckgo.com/?q=" + search_query)
                current_tab = self.get_current_tab()
                if current_tab:
                    current_tab.setUrl(search_url)
            else:
                current_tab = self.get_current_tab()
                if current_tab:
                    current_tab.setUrl(q)

    def update_urlbar(self, q, browser=None):
        if browser != self.get_current_tab():
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

    def update_tab_title(self, title):
        current_tab = self.tabs.currentWidget()
        index = self.tabs.indexOf(current_tab)
        self.tabs.setTabText(index, title)

    def close_current_tab_shortcut(self):
        current_index = self.tabs.currentIndex()
        if current_index >= 0:
            self.close_current_tab(current_index)

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


home = "https://duckduckgo.com/"


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    app.setWindowIcon(QIcon(resource_path('logo.ico')))
    app.setApplicationName("RamBrowse")
    app.setOrganizationName("DoesArt Studios")
    app.setOrganizationDomain("https://DoesArt-Studios.gihtub.io/RamBrowseWebsite/")

    app.exec()

if __name__ == '__main__':
    main()
