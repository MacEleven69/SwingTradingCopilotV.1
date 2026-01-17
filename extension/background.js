/**
 * Background Service Worker for Swing Trading Copilot
 * Handles side panel functionality
 */

// Listen for extension installation
chrome.runtime.onInstalled.addListener(async () => {
    // Check if side panel is supported
    if (chrome.sidePanel) {
        console.log('✅ Side panel API available');
        
        // Optional: Set side panel behavior for all tabs
        try {
            await chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true });
            console.log('✅ Side panel will open on icon click');
        } catch (error) {
            console.log('⚠️ Could not set panel behavior:', error);
        }
    } else {
        console.log('❌ Side panel API not available - Chrome 114+ required');
    }
});

// Optional: Add context menu for quick access
chrome.runtime.onInstalled.addListener(() => {
    // Create context menu item to open side panel
    if (chrome.contextMenus) {
        chrome.contextMenus.create({
            id: 'openSidePanel',
            title: '📌 Open in Side Panel',
            contexts: ['action']
        });
    }
    
    console.log('Swing Trading Copilot installed');
});

// Handle context menu clicks
if (chrome.contextMenus) {
    chrome.contextMenus.onClicked.addListener(async (info, tab) => {
        if (info.menuItemId === 'openSidePanel' && chrome.sidePanel) {
            try {
                await chrome.sidePanel.open({ windowId: tab.windowId });
            } catch (error) {
                console.error('Error opening side panel from menu:', error);
            }
        }
    });
}

// Optional: Set side panel behavior (open on specific websites)
// Uncomment if you want to auto-open on financial websites
/*
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        // Auto-open on financial websites
        const financialSites = ['finance.yahoo.com', 'tradingview.com', 'robinhood.com'];
        const shouldOpen = financialSites.some(site => tab.url.includes(site));
        
        if (shouldOpen && chrome.sidePanel) {
            chrome.sidePanel.open({ windowId: tab.windowId });
        }
    }
});
*/

