document.addEventListener('DOMContentLoaded', function() {
  const showBannerBtn = document.getElementById('show-banner');
  const hideBannerBtn = document.getElementById('hide-banner');
  const clearStatsBtn = document.getElementById('clear-stats');

  function updateStatsDisplay() {
    chrome.storage.local.get(['extensionStats'], function(result) {
      const stats = result.extensionStats || {
        installDate: Date.now(),
        bannerShows: 0,
        popupOpens: 0,
        lastSeen: Date.now()
      };

      const installDate = new Date(stats.installDate).toLocaleDateString();
      const lastSeen = new Date(stats.lastSeen).toLocaleString();

      document.getElementById('stats-content').innerHTML = `
        <div style="font-size: 11px; line-height: 1.4;">
          • Installed: ${installDate}<br>
          • Banner shows: ${stats.bannerShows}<br>
          • Popup opens: ${stats.popupOpens}<br>
          • Last seen: ${lastSeen}
        </div>
      `;

      if (!result.extensionStats) {
        chrome.storage.local.set({extensionStats: stats});
      }
    });
  }

  function incrementPopupCount() {
    chrome.storage.local.get(['extensionStats'], function(result) {
      const stats = result.extensionStats || {
        installDate: Date.now(),
        bannerShows: 0,
        popupOpens: 0,
        lastSeen: Date.now()
      };
      stats.popupOpens++;
      stats.lastSeen = Date.now();
      chrome.storage.local.set({extensionStats: stats}, function() {
        updateStatsDisplay();
      });
    });
  }

  showBannerBtn.addEventListener('click', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      chrome.scripting.executeScript({
        target: {tabId: tabs[0].id},
        function: showHelloWorldBanner
      });
      updateStatsDisplay();
    });
  });

  hideBannerBtn.addEventListener('click', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      chrome.scripting.executeScript({
        target: {tabId: tabs[0].id},
        function: hideHelloWorldBanner
      });
    });
  });

  clearStatsBtn.addEventListener('click', function() {
    chrome.storage.local.remove(['extensionStats'], function() {
      updateStatsDisplay();
    });
  });

  // Initialize stats display and increment popup count
  incrementPopupCount();
});

function showHelloWorldBanner() {
  if (document.getElementById('web-notes-hello-banner')) {
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
      <span class="banner-message">Web Notes - Popup Triggered!</span>
      <span class="banner-close" style="margin-left: 8px; opacity: 0.7; font-size: 18px; cursor: pointer; padding: 4px;">×</span>
    </div>
  `;

  const style = document.createElement('style');
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

  if (!document.querySelector('style[data-web-notes-banner]')) {
    style.setAttribute('data-web-notes-banner', 'true');
    document.head.appendChild(style);
  }

  document.body.appendChild(banner);

  // Add click handler for the main banner (not the close button)
  const messageArea = banner.querySelector('.banner-message');
  messageArea.addEventListener('click', function(e) {
    e.stopPropagation();
    alert('Hello from Web Notes Chrome Extension!\\n\\nTriggered from popup button.');
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

  chrome.storage.local.get(['extensionStats'], function(result) {
    const stats = result.extensionStats || { installDate: Date.now(), bannerShows: 0 };
    stats.bannerShows++;
    chrome.storage.local.set({extensionStats: stats});
  });
}

function hideHelloWorldBanner() {
  const banner = document.getElementById('web-notes-hello-banner');
  if (banner) {
    banner.style.animation = 'slideOut 0.3s ease-in forwards';

    const style = document.createElement('style');
    style.textContent = `
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
    `;
    document.head.appendChild(style);

    setTimeout(() => {
      if (banner.parentNode) {
        banner.remove();
      }
    }, 300);
  }
}