document.addEventListener('DOMContentLoaded', function() {
  const showBannerBtn = document.getElementById('show-banner');
  const hideBannerBtn = document.getElementById('hide-banner');

  showBannerBtn.addEventListener('click', function() {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      chrome.scripting.executeScript({
        target: {tabId: tabs[0].id},
        function: showHelloWorldBanner
      });
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

  chrome.storage.local.get(['extensionStats'], function(result) {
    const stats = result.extensionStats || { installDate: Date.now(), bannerShows: 0 };
    console.log('Extension stats:', stats);

    if (!result.extensionStats) {
      chrome.storage.local.set({extensionStats: stats});
    }
  });
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
      <span>Web Notes - Popup Triggered!</span>
      <span style="margin-left: 8px; opacity: 0.7; font-size: 18px;" onclick="this.parentElement.parentElement.remove()">×</span>
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

    #web-notes-hello-banner:hover {
      transform: scale(1.05);
      box-shadow: 0 6px 25px rgba(0, 0, 0, 0.2);
    }
  `;

  if (!document.querySelector('style[data-web-notes-banner]')) {
    style.setAttribute('data-web-notes-banner', 'true');
    document.head.appendChild(style);
  }

  document.body.appendChild(banner);

  banner.addEventListener('click', function() {
    alert('Hello from Web Notes Chrome Extension!\\n\\nTriggered from popup button.');
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