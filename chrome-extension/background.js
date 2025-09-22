// Background script for Web Notes Chrome Extension
// Handles context menu creation and click events

chrome.runtime.onInstalled.addListener(() => {
  console.log('Web Notes extension installed/updated');

  // Create context menu item
  chrome.contextMenus.create({
    id: 'show-web-notes-banner',
    title: '🗒️ Show Web Notes Banner',
    contexts: ['page', 'selection', 'link', 'image']
  });

  // Initialize extension stats if needed
  chrome.storage.local.get(['extensionStats'], (result) => {
    if (!result.extensionStats) {
      const stats = {
        installDate: Date.now(),
        bannerShows: 0,
        popupOpens: 0,
        contextMenuClicks: 0,
        lastSeen: Date.now()
      };
      chrome.storage.local.set({extensionStats: stats});
    }
  });
});

// Handle context menu clicks
chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'show-web-notes-banner') {
    // Inject the banner into the current tab
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      function: showWebNotesBanner
    });

    // Update stats
    chrome.storage.local.get(['extensionStats'], (result) => {
      const stats = result.extensionStats || {
        installDate: Date.now(),
        bannerShows: 0,
        popupOpens: 0,
        contextMenuClicks: 0,
        lastSeen: Date.now()
      };
      stats.contextMenuClicks++;
      stats.bannerShows++;
      stats.lastSeen = Date.now();
      chrome.storage.local.set({extensionStats: stats});
    });
  }
});

// Function to be injected into the web page
function showWebNotesBanner() {
  // Check if banner already exists
  if (document.getElementById('web-notes-hello-banner')) {
    // If it exists, just make it visible and add a pulse effect
    const existingBanner = document.getElementById('web-notes-hello-banner');
    existingBanner.style.animation = 'pulse 0.5s ease-in-out';
    setTimeout(() => {
      existingBanner.style.animation = '';
    }, 500);
    return;
  }

  const banner = document.createElement('div');
  banner.id = 'web-notes-hello-banner';
  banner.style.cssText = `
    position: fixed;
    top: 10px;
    right: 10px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 20px;
    border-radius: 8px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 14px;
    font-weight: 600;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    z-index: 10000;
    cursor: pointer;
    animation: slideIn 0.3s ease-out;
    transition: all 0.3s ease;
  `;

  banner.innerHTML = `
    <div style="display: flex; align-items: center; gap: 8px;">
      <span>🗒️</span>
      <span class="banner-message">Web Notes - Context Menu!</span>
      <span class="banner-close" style="margin-left: 8px; opacity: 0.7; font-size: 18px; cursor: pointer; padding: 4px;">×</span>
    </div>
  `;

  // Add styles if not already present
  if (!document.querySelector('style[data-web-notes-banner]')) {
    const style = document.createElement('style');
    style.setAttribute('data-web-notes-banner', 'true');
    style.textContent = `
      @keyframes slideIn {
        from {
          transform: translateX(100%);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }

      @keyframes slideOut {
        from {
          transform: translateX(0);
          opacity: 1;
        }
        to {
          transform: translateX(100%);
          opacity: 0;
        }
      }

      @keyframes pulse {
        0%, 100% {
          transform: scale(1);
        }
        50% {
          transform: scale(1.05);
        }
      }

      #web-notes-hello-banner:hover {
        transform: scale(1.05);
        box-shadow: 0 6px 25px rgba(0, 0, 0, 0.2);
      }

      .banner-close:hover {
        opacity: 1 !important;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 50%;
      }
    `;
    document.head.appendChild(style);
  }

  document.body.appendChild(banner);

  // Add click handler for the main banner message
  const messageArea = banner.querySelector('.banner-message');
  messageArea.addEventListener('click', function(e) {
    e.stopPropagation();
    alert('Hello from Web Notes Chrome Extension!\\n\\nTriggered from right-click context menu.');
  });

  // Add click handler for the close button
  const closeButton = banner.querySelector('.banner-close');
  closeButton.addEventListener('click', function(e) {
    e.stopPropagation();
    banner.style.animation = 'slideOut 0.3s ease-in forwards';
    setTimeout(() => {
      if (banner.parentNode) {
        banner.remove();
      }
    }, 300);
  });

  // Auto-fade after 5 seconds (optional)
  setTimeout(() => {
    if (banner.parentNode) {
      banner.style.opacity = '0.8';
    }
  }, 5000);
}