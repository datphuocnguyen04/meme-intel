const form = document.getElementById('search-form');
        const input = document.getElementById('contract-input');
        const btn = document.getElementById('search-btn');
        const loadingState = document.getElementById('loading-state');
        const errorState = document.getElementById('error-state');
        const resultsArea = document.getElementById('results-area');
        const errorMsg = document.getElementById('error-msg');
        const loadingMsg = document.getElementById('loading-msg');

        // Modal Elements & Handlers
        const imageModal = document.getElementById('image-modal');
        const modalImage = document.getElementById('modal-image');
        const modalCaption = document.getElementById('modal-caption');
        const modalCloseBtn = document.getElementById('modal-close-btn');

        function openImageModal(imgSrc, title, subtitle) {
            if (!imgSrc) return;
            modalImage.src = imgSrc;
            modalCaption.innerHTML = `${escapeHtml(title)}${subtitle ? `<small>${escapeHtml(subtitle)}</small>` : ''}`;
            imageModal.style.display = 'flex';
        }

        function closeImageModal() {
            imageModal.style.display = 'none';
            modalImage.src = '';
        }

        modalCloseBtn.addEventListener('click', closeImageModal);
        imageModal.addEventListener('click', (e) => {
            if (e.target.id === 'image-modal') {
                closeImageModal();
            }
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && imageModal.style.display === 'flex') {
                closeImageModal();
            }
        });

        // Click on Token Profile Image to Pop Up
        document.getElementById('token-image').addEventListener('click', () => {
            const tokenImg = document.getElementById('token-image');
            const tokenName = document.getElementById('token-name').textContent;
            const tokenSymbol = document.getElementById('token-symbol').textContent;
            if (tokenImg.src && tokenImg.style.display !== 'none') {
                openImageModal(tokenImg.src, `${tokenName} (${tokenSymbol})`, 'Token Profile Symbol');
            }
        });

        // Contract Copy Setup & Functionality (Bulletproof Cross-Browser)
        let rawContractAddress = '';

        function setupContractCopy(address) {
            rawContractAddress = (address || '').trim();
            const displayEl = document.getElementById('contract-address-display');
            const copyRow = document.getElementById('contract-copy-row');
            
            if (rawContractAddress) {
                copyRow.setAttribute('data-contract', rawContractAddress);
                displayEl.textContent = formatTruncatedAddress(rawContractAddress);
                copyRow.style.display = 'inline-flex';
            } else {
                copyRow.style.display = 'none';
            }
        }

        function formatTruncatedAddress(addr) {
            if (!addr) return '';
            if (addr.length <= 18) return addr;
            return `${addr.slice(0, 8)}...${addr.slice(-6)}`;
        }

        function fallbackCopyText(text) {
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.setAttribute('readonly', '');
            textArea.style.position = 'fixed';
            textArea.style.left = '-9999px';
            textArea.style.top = '-9999px';
            textArea.style.opacity = '0';
            textArea.style.fontSize = '16px'; // Prevents mobile viewport zooming
            document.body.appendChild(textArea);

            textArea.focus();
            textArea.select();
            textArea.setSelectionRange(0, 99999);

            let copied = false;
            try {
                copied = document.execCommand('copy');
            } catch (err) {
                console.error('execCommand copy failed:', err);
            }
            document.body.removeChild(textArea);
            return copied;
        }

        function copyContractToClipboard(e) {
            if (e) {
                e.preventDefault();
                e.stopPropagation();
            }

            const addr = rawContractAddress || 
                         document.getElementById('contract-copy-row')?.getAttribute('data-contract') || 
                         currentContract || 
                         document.getElementById('contract-input')?.value.trim();

            if (!addr) {
                console.warn('No contract address available to copy');
                return;
            }

            // 1. Try modern async clipboard if available and in secure context
            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(addr).then(() => {
                    triggerCopyFeedback();
                }).catch(() => {
                    // Fallback if permission was denied
                    if (fallbackCopyText(addr)) {
                        triggerCopyFeedback();
                    } else {
                        window.prompt("Copy contract address:", addr);
                    }
                });
            } else {
                // 2. Synchronous fallback within active user click gesture
                if (fallbackCopyText(addr)) {
                    triggerCopyFeedback();
                } else {
                    window.prompt("Copy contract address:", addr);
                }
            }
        }

        function triggerCopyFeedback() {
            const copyBtn = document.getElementById('copy-contract-btn');
            const copyStatus = document.getElementById('copy-status-text');
            if (copyBtn && copyStatus) {
                copyBtn.classList.add('copied');
                copyStatus.textContent = 'Copied! ✓';
                setTimeout(() => {
                    copyBtn.classList.remove('copied');
                    copyStatus.textContent = 'Copy';
                }, 2000);
            }
        }

        const copyRowEl = document.getElementById('contract-copy-row');
        const copyBtnEl = document.getElementById('copy-contract-btn');
        if (copyRowEl) copyRowEl.addEventListener('click', copyContractToClipboard);
        if (copyBtnEl) copyBtnEl.addEventListener('click', copyContractToClipboard);

        // ================= CHAIN SYMBOLS & BADGES =================
        // DexScreener CDN chain image URLs
        const CHAIN_IMAGE_URLS = {
            solana:    'https://dd.dexscreener.com/ds-data/chains/solana.png',
            sol:       'https://dd.dexscreener.com/ds-data/chains/solana.png',
            ethereum:  'https://dd.dexscreener.com/ds-data/chains/ethereum.png',
            eth:       'https://dd.dexscreener.com/ds-data/chains/ethereum.png',
            base:      'https://dd.dexscreener.com/ds-data/chains/base.png',
            robinhood: 'https://dd.dexscreener.com/ds-data/chains/robinhood.png',
            rh:        'https://dd.dexscreener.com/ds-data/chains/robinhood.png',
            ink:       'https://dd.dexscreener.com/ds-data/chains/ink.png',
            bsc:       'https://dd.dexscreener.com/ds-data/chains/bsc.png',
            binance:   'https://dd.dexscreener.com/ds-data/chains/bsc.png',
            arbitrum:  'https://dd.dexscreener.com/ds-data/chains/arbitrum.png',
            arb:       'https://dd.dexscreener.com/ds-data/chains/arbitrum.png',
            polygon:   'https://dd.dexscreener.com/ds-data/chains/polygon.png',
            matic:     'https://dd.dexscreener.com/ds-data/chains/polygon.png',
            avalanche: 'https://dd.dexscreener.com/ds-data/chains/avalanche.png',
            avax:      'https://dd.dexscreener.com/ds-data/chains/avalanche.png',
            optimism:  'https://dd.dexscreener.com/ds-data/chains/optimism.png',
            op:        'https://dd.dexscreener.com/ds-data/chains/optimism.png',
        };

        function getChainInfo(chainRaw) {
            const c = (chainRaw || '').toLowerCase().trim();
            const imageUrl = CHAIN_IMAGE_URLS[c] || `https://dd.dexscreener.com/ds-data/chains/${c}.png`;
            if (c === 'solana' || c === 'sol') {
                return { symbol: 'SOL', name: 'Solana', color: '#14F195', bgColor: 'rgba(20,241,149,0.15)', borderColor: 'rgba(20,241,149,0.35)', imageUrl };
            }
            if (c === 'ethereum' || c === 'eth') {
                return { symbol: 'ETH', name: 'Ethereum', color: '#8A92B2', bgColor: 'rgba(98,126,234,0.15)', borderColor: 'rgba(98,126,234,0.35)', imageUrl };
            }
            if (c === 'base') {
                return { symbol: 'BASE', name: 'Base', color: '#3b82f6', bgColor: 'rgba(0,82,255,0.15)', borderColor: 'rgba(0,82,255,0.35)', imageUrl };
            }
            if (c === 'robinhood' || c === 'rh') {
                return { symbol: 'ROBI', name: 'Robinhood', color: '#00C805', bgColor: 'rgba(0,200,5,0.15)', borderColor: 'rgba(0,200,5,0.35)', imageUrl };
            }
            if (c === 'ink') {
                return { symbol: 'INK', name: 'Ink', color: '#c084fc', bgColor: 'rgba(168,85,247,0.15)', borderColor: 'rgba(168,85,247,0.35)', imageUrl };
            }
            if (c === 'bsc' || c === 'binance') {
                return { symbol: 'BNB', name: 'BNB Chain', color: '#F3BA2F', bgColor: 'rgba(243,186,47,0.15)', borderColor: 'rgba(243,186,47,0.35)', imageUrl };
            }
            if (c === 'arbitrum' || c === 'arb') {
                return { symbol: 'ARB', name: 'Arbitrum', color: '#28A0F0', bgColor: 'rgba(40,160,240,0.15)', borderColor: 'rgba(40,160,240,0.35)', imageUrl };
            }
            if (c === 'polygon' || c === 'matic') {
                return { symbol: 'POL', name: 'Polygon', color: '#a855f7', bgColor: 'rgba(130,71,229,0.15)', borderColor: 'rgba(130,71,229,0.35)', imageUrl };
            }
            if (c === 'avalanche' || c === 'avax') {
                return { symbol: 'AVAX', name: 'Avalanche', color: '#ef4444', bgColor: 'rgba(239,68,68,0.15)', borderColor: 'rgba(239,68,68,0.35)', imageUrl };
            }
            if (c === 'optimism' || c === 'op') {
                return { symbol: 'OP', name: 'Optimism', color: '#ff0420', bgColor: 'rgba(255,4,32,0.15)', borderColor: 'rgba(255,4,32,0.35)', imageUrl };
            }
            const sym = (c ? c.slice(0, 4) : 'GEN').toUpperCase();
            return { symbol: sym, name: chainRaw || 'Unknown', color: '#9ca3af', bgColor: 'rgba(156,163,175,0.15)', borderColor: 'rgba(156,163,175,0.35)', imageUrl };
        }

        function renderChainBadgeHtml(chain) {
            const info = getChainInfo(chain);
            return `<span class="chain-symbol-badge" title="${escapeHtml(info.name)}"><img class="chain-symbol-img" src="${info.imageUrl}" alt="${escapeHtml(info.symbol)}" onerror="this.style.display='none'"></span>`;
        }

        function getDefaultQuote(chain) {
            const c = (chain || '').toLowerCase();
            if (c === 'solana' || c === 'sol') return 'SOL';
            if (c === 'robinhood' || c === 'rh') return 'AMZN';
            if (c === 'bsc' || c === 'binance') return 'BNB';
            if (c === 'polygon' || c === 'matic') return 'POL';
            return 'ETH';
        }

        function getPairLabel(item) {
            if (item.pair_label && item.pair_label.includes('/')) return item.pair_label;
            const base = item.symbol || '???';
            let quote = item.quote_symbol || '';
            if (!quote) {
                if (base.toUpperCase() === 'WADDLES' && (item.chain || '').toLowerCase().includes('robin')) {
                    quote = 'AMZN';
                } else {
                    quote = getDefaultQuote(item.chain);
                }
            }
            return quote ? `${base}/${quote}` : base;
        }

        // ================= WATCHLIST SYSTEM =================
        const WATCHLIST_STORAGE_KEY = 'memecoin_watchlist_v1';
        let currentTokenInfo = null;

        function getWatchlist() {
            try {
                const raw = localStorage.getItem(WATCHLIST_STORAGE_KEY);
                return raw ? JSON.parse(raw) : [];
            } catch (e) {
                console.error('Failed to parse watchlist:', e);
                return [];
            }
        }

        function saveWatchlist(list) {
            try {
                localStorage.setItem(WATCHLIST_STORAGE_KEY, JSON.stringify(list));
            } catch (e) {
                console.error('Failed to save watchlist:', e);
            }
        }

        function isTokenInWatchlist(contract) {
            if (!contract) return false;
            const list = getWatchlist();
            const normalized = contract.trim().toLowerCase();
            return list.some(item => (item.contract || '').toLowerCase() === normalized);
        }

        function toggleWatchlist(token) {
            if (!token) return;
            const contract = token.contract_address || currentContract || token.pair_address || input.value.trim();
            if (!contract) return;

            let list = getWatchlist();
            const normalized = contract.trim().toLowerCase();
            const existsIndex = list.findIndex(item => (item.contract || '').toLowerCase() === normalized);

            let isNowWatched = false;
            if (existsIndex >= 0) {
                // Remove from list
                list.splice(existsIndex, 1);
                isNowWatched = false;
                saveWatchlist(list);
                updateWatchlistToggleBtn(false);
            } else {
                // Add to list
                const quoteSymbol = token.quote_symbol || (token.pair_label ? token.pair_label.split('/')[1] : '') || getDefaultQuote(token.chain);
                const pairLabel = token.pair_label || (token.symbol ? `${token.symbol}/${quoteSymbol || 'USD'}` : '???');

                const newItem = {
                    contract: contract,
                    name: token.name || 'Unknown',
                    symbol: token.symbol || '???',
                    quote_symbol: quoteSymbol,
                    pair_label: pairLabel,
                    chain: token.chain || 'unknown',
                    image_url: token.image_url || '',
                    price_usd: token.price_usd || '0',
                    price_change_24h: token.price_change?.h24 ?? null,
                    added_at: Date.now()
                };
                list.unshift(newItem); // newest first
                isNowWatched = true;
                saveWatchlist(list);
                updateWatchlistToggleBtn(true);
            }

            // Sync with backend SQLite
            fetch(`/api/watchlist/${encodeURIComponent(contract)}/toggle`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ is_watchlist: isNowWatched, token: token })
            }).catch(e => console.warn('Failed to sync watchlist with SQLite:', e));

            renderWatchlistUI();
        }

        async function syncWatchlistFromDB() {
            try {
                const res = await fetch('/api/watchlist');
                if (res.ok) {
                    const data = await res.json();
                    if (data.watchlist && Array.isArray(data.watchlist) && data.watchlist.length > 0) {
                        let local = getWatchlist();
                        let changed = false;
                        data.watchlist.forEach(dbItem => {
                            const exists = local.some(l => (l.contract || '').toLowerCase() === (dbItem.contract_address || '').toLowerCase());
                            if (!exists) {
                                const quoteSymbol = dbItem.quote_symbol || getDefaultQuote(dbItem.chain);
                                const pairLabel = dbItem.pair_label || (dbItem.symbol ? `${dbItem.symbol}/${quoteSymbol}` : '???');
                                local.push({
                                    contract: dbItem.contract_address,
                                    name: dbItem.name || 'Unknown',
                                    symbol: dbItem.symbol || '???',
                                    quote_symbol: quoteSymbol,
                                    pair_label: pairLabel,
                                    chain: dbItem.chain || 'unknown',
                                    image_url: dbItem.image_url || '',
                                    price_usd: '0',
                                    price_change_24h: null,
                                    added_at: Date.now()
                                });
                                changed = true;
                            }
                        });
                        if (changed) {
                            saveWatchlist(local);
                            renderWatchlistUI();
                            refreshAllWatchlistPrices();
                        }
                    }
                }
            } catch (e) {
                console.warn('Could not sync initial watchlist from SQLite:', e);
            }
        }

        function updateWatchlistToggleBtn(isInList) {
            const btn = document.getElementById('watchlist-toggle-btn');
            const icon = document.getElementById('star-icon');
            const text = document.getElementById('star-text');
            if (!btn) return;

            if (isInList) {
                btn.classList.add('active');
                if (icon) icon.textContent = '★';
                if (text) text.textContent = 'Watching';
                btn.title = 'Remove from Watchlist';
            } else {
                btn.classList.remove('active');
                if (icon) icon.textContent = '☆';
                if (text) text.textContent = 'Watchlist';
                btn.title = 'Add to Watchlist';
            }
        }

        function renderWatchlistUI() {
            const section = document.getElementById('watchlist-section');
            const container = document.getElementById('watchlist-items');
            const countBadge = document.getElementById('watchlist-count');
            if (!section || !container) return;

            const list = getWatchlist();
            if (countBadge) countBadge.textContent = list.length;

            if (list.length === 0) {
                section.style.display = 'none';
                container.innerHTML = '';
                return;
            }

            section.style.display = 'block';
            container.innerHTML = '';

            list.forEach(item => {
                const div = document.createElement('div');
                div.className = 'watchlist-item';
                div.setAttribute('data-contract', item.contract);

                const imgHtml = item.image_url 
                    ? `<img class="watchlist-item-img" src="${item.image_url}" alt="${escapeHtml(item.symbol)}" onerror="this.src='https://ui-avatars.com/api/?name=${encodeURIComponent(item.symbol)}&background=1f1f2e&color=fff';">`
                    : `<div class="watchlist-item-img" style="display:flex;align-items:center;justify-content:center;font-size:0.75rem;font-weight:700;color:#9ca3af;background:#1f1f2e;">$</div>`;

                const changeHtml = item.price_change_24h !== null && item.price_change_24h !== undefined
                    ? formatPercent(item.price_change_24h)
                    : '<span style="color:#6b7280;">-</span>';

                const pairLabel = getPairLabel(item);
                const chainBadgeHtml = renderChainBadgeHtml(item.chain);

                div.innerHTML = `
                    <div class="watchlist-item-left">
                        ${imgHtml}
                        <div class="watchlist-item-info">
                            <div class="watchlist-item-sym">
                                <span class="watchlist-item-pair">${escapeHtml(pairLabel)}</span>
                            </div>
                            <div class="watchlist-item-name">${escapeHtml(item.name)}</div>
                        </div>
                    </div>
                    <div class="watchlist-item-right">
                        ${chainBadgeHtml}
                        <div class="watchlist-item-change">${changeHtml}</div>
                    </div>
                    <button type="button" class="watchlist-remove-btn" title="Remove from Watchlist">&times;</button>
                `;

                // Click chip to analyze token
                div.addEventListener('click', (e) => {
                    if (e.target.classList.contains('watchlist-remove-btn')) return;
                    input.value = item.contract;
                    form.dispatchEvent(new Event('submit'));
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                });

                // Click remove button
                const removeBtn = div.querySelector('.watchlist-remove-btn');
                if (removeBtn) {
                    removeBtn.addEventListener('click', (e) => {
                        e.stopPropagation();
                        let currentList = getWatchlist();
                        currentList = currentList.filter(x => (x.contract || '').toLowerCase() !== (item.contract || '').toLowerCase());
                        saveWatchlist(currentList);
                        renderWatchlistUI();
                        // Update current star button if active
                        const currentKey = currentTokenInfo?.contract_address || currentContract || '';
                        if (currentKey && currentKey.toLowerCase() === (item.contract || '').toLowerCase()) {
                            updateWatchlistToggleBtn(false);
                        }
                    });
                }

                container.appendChild(div);
            });
        }

        async function refreshAllWatchlistPrices() {
            const list = getWatchlist();
            if (list.length === 0) return;

            const refreshBtn = document.getElementById('refresh-watchlist-btn');
            if (refreshBtn) {
                refreshBtn.disabled = true;
                refreshBtn.textContent = 'Refreshing...';
            }

            let updated = false;
            await Promise.all(list.map(async (item, idx) => {
                try {
                    const res = await fetch(`/api/token/${encodeURIComponent(item.contract)}/price`);
                    if (res.ok) {
                        const data = await res.json();
                        if (data.token) {
                            list[idx].price_usd = data.token.price_usd;
                            list[idx].price_change_24h = data.token.price_change?.h24 ?? null;
                            if (data.token.image_url) list[idx].image_url = data.token.image_url;
                            updated = true;
                        }
                    }
                } catch (err) {
                    console.warn(`Failed to refresh price for ${item.symbol}:`, err);
                }
            }));

            if (updated) {
                saveWatchlist(list);
                renderWatchlistUI();
            }

            if (refreshBtn) {
                refreshBtn.disabled = false;
                refreshBtn.textContent = '🔄 Refresh Prices';
            }
        }

        // Wire Watchlist Star toggle
        const watchlistToggleBtn = document.getElementById('watchlist-toggle-btn');
        if (watchlistToggleBtn) {
            watchlistToggleBtn.addEventListener('click', () => {
                if (currentTokenInfo) {
                    toggleWatchlist(currentTokenInfo);
                }
            });
        }

        // Wire Watchlist Refresh button
        const refreshWatchlistBtn = document.getElementById('refresh-watchlist-btn');
        if (refreshWatchlistBtn) {
            refreshWatchlistBtn.addEventListener('click', refreshAllWatchlistPrices);
        }

        // Initialize Watchlist on startup
        renderWatchlistUI();
        refreshAllWatchlistPrices();
        syncWatchlistFromDB();

        // Wire Refresh X Tweets & Story button
        const refreshXBtn = document.getElementById('refresh-x-btn');
        const refreshXBtnText = document.getElementById('refresh-x-btn-text');

        if (refreshXBtn) {
            refreshXBtn.addEventListener('click', async () => {
                const contract = currentContract || input.value.trim();
                if (!contract) return;

                refreshXBtn.disabled = true;
                if (refreshXBtnText) refreshXBtnText.textContent = 'Fetching X & AI...';

                try {
                    const res = await fetch(`/api/token/${encodeURIComponent(contract)}/refresh-tweets`, {
                        method: 'POST',
                    });
                    if (!res.ok) {
                        throw new Error("Failed to refresh tweets from X");
                    }
                    const updatedData = await res.json();
                    populateData(updatedData);

                    // Show success feedback
                    if (refreshXBtnText) refreshXBtnText.textContent = 'Updated! ✓';
                    setTimeout(() => {
                        if (refreshXBtnText) refreshXBtnText.textContent = 'Refresh X Tweets & Story';
                    }, 2000);
                } catch (err) {
                    console.error("Error refreshing X tweets:", err);
                    alert("Error updating from X: " + (err.message || "Request failed"));
                    if (refreshXBtnText) refreshXBtnText.textContent = 'Refresh X Tweets & Story';
                } finally {
                    refreshXBtn.disabled = false;
                }
            });
        }

        // Live Auto-Refresh State
        let currentContract = null;
        let countdownTimer = null;
        let countdownSec = 10;
        let isPaused = false;
        let lastPrice = null;

        const toggleRefreshBtn = document.getElementById('toggle-refresh-btn');
        const manualRefreshBtn = document.getElementById('manual-refresh-btn');
        const liveDot = document.getElementById('live-dot');
        const liveText = document.getElementById('live-text');

        toggleRefreshBtn.addEventListener('click', () => {
            isPaused = !isPaused;
            if (isPaused) {
                toggleRefreshBtn.textContent = 'Resume';
                liveDot.classList.add('paused');
                liveText.innerHTML = '<span style="color: #9ca3af;">Live Price: Paused</span>';
            } else {
                toggleRefreshBtn.textContent = 'Pause';
                liveDot.classList.remove('paused');
                countdownSec = 10;
                updateCountdownDisplay();
            }
        });

        manualRefreshBtn.addEventListener('click', async () => {
            if (currentContract) {
                manualRefreshBtn.disabled = true;
                manualRefreshBtn.textContent = 'Refreshing...';
                await refreshPriceOnly();
                manualRefreshBtn.disabled = false;
                manualRefreshBtn.textContent = '⚡ Refresh Now';
                countdownSec = 10;
                updateCountdownDisplay();
            }
        });

        function updateCountdownDisplay() {
            if (!isPaused && liveText) {
                liveText.innerHTML = `Live Price: Auto-refreshing in <span id="countdown-sec" style="color: #60a5fa; font-weight: 700;">${countdownSec}</span>s`;
            }
        }

        function startAutoRefreshTimer() {
            if (countdownTimer) clearInterval(countdownTimer);
            countdownSec = 10;
            updateCountdownDisplay();

            countdownTimer = setInterval(async () => {
                if (isPaused || !currentContract) return;

                countdownSec--;
                if (countdownSec <= 0) {
                    countdownSec = 10;
                    updateCountdownDisplay();
                    await refreshPriceOnly();
                } else {
                    updateCountdownDisplay();
                }
            }, 1000);
        }

        async function refreshPriceOnly() {
            if (!currentContract) return;
            try {
                const res = await fetch(`/api/token/${encodeURIComponent(currentContract)}/price`);
                if (res.ok) {
                    const data = await res.json();
                    if (data.token) {
                        updateMarketMetricsOnly(data.token);
                    }
                }
            } catch (e) {
                console.error("Failed to auto-refresh price:", e);
            }
        }

        function updateMarketMetricsOnly(token) {
            const priceEl = document.getElementById('token-price');
            const newPrice = parseFloat(token.price_usd);

            if (lastPrice !== null && !isNaN(newPrice) && !isNaN(lastPrice)) {
                priceEl.classList.remove('price-flash-green', 'price-flash-red');
                void priceEl.offsetWidth; // Trigger DOM reflow to restart CSS animation
                if (newPrice > lastPrice) {
                    priceEl.classList.add('price-flash-green');
                } else if (newPrice < lastPrice) {
                    priceEl.classList.add('price-flash-red');
                }
            }
            lastPrice = isNaN(newPrice) ? null : newPrice;

            priceEl.textContent = formatPrice(token.price_usd);
            document.getElementById('mcap').textContent = formatCompactNumber(token.market_cap);
            document.getElementById('fdv').textContent = formatCompactNumber(token.fdv);
            const supplyEl = document.getElementById('total-supply');
            if (supplyEl) {
                if (token.total_supply) {
                    supplyEl.textContent = formatTokenSupply(token.total_supply);
                    supplyEl.title = `${Number(token.total_supply).toLocaleString()} tokens`;
                } else if (supplyEl.textContent === '-' || supplyEl.textContent === '--') {
                    supplyEl.textContent = '-';
                }
            }
            document.getElementById('volume').textContent = formatCompactNumber(token.volume_24h);
            document.getElementById('liquidity').textContent = formatCompactNumber(token.liquidity_usd);
            
            document.getElementById('buys').textContent = (token.txns_24h?.buys || 0).toLocaleString();
            document.getElementById('sells').textContent = (token.txns_24h?.sells || 0).toLocaleString();

            // Buy & Sell Taxes
            const buyTaxEl = document.getElementById('buy-tax');
            const sellTaxEl = document.getElementById('sell-tax');
            const buyTaxVal = token.buy_tax || '0%';
            const sellTaxVal = token.sell_tax || '0%';

            buyTaxEl.textContent = buyTaxVal;
            sellTaxEl.textContent = sellTaxVal;

            buyTaxEl.style.color = (buyTaxVal === '0%' || buyTaxVal === '0.0%') ? 'var(--positive)' : (parseFloat(buyTaxVal) > 5 ? 'var(--negative)' : '#facc15');
            sellTaxEl.style.color = (sellTaxVal === '0%' || sellTaxVal === '0.0%') ? 'var(--positive)' : (parseFloat(sellTaxVal) > 5 ? 'var(--negative)' : '#facc15');

            document.getElementById('pair-age').textContent = formatRelativeTime(token.created_at);
            document.getElementById('dex-name').textContent = token.dex || 'Unknown DEX';
            document.getElementById('dexscreener-link').href = token.pair_url || '#';

            // Price Changes
            const changesContainer = document.getElementById('price-changes-container');
            changesContainer.innerHTML = '';
            const periods = ['m5', 'h1', 'h6', 'h24'];
            const labels = { m5: '5M', h1: '1H', h6: '6H', h24: '24H' };
            
            periods.forEach(p => {
                if (token.price_change && token.price_change[p] !== undefined && token.price_change[p] !== null) {
                    const div = document.createElement('div');
                    div.className = 'change-item';
                    div.innerHTML = `<span class="change-label">${labels[p]}:</span> ${formatPercent(token.price_change[p])}`;
                    changesContainer.appendChild(div);
                }
            });

            // Keep Watchlist card prices in sync if this token is currently in the watchlist
            const contractKey = (token.contract_address || currentContract || token.pair_address || '').toLowerCase();
            if (contractKey) {
                let list = getWatchlist();
                const idx = list.findIndex(x => (x.contract || '').toLowerCase() === contractKey);
                if (idx >= 0) {
                    list[idx].price_usd = token.price_usd;
                    list[idx].price_change_24h = token.price_change?.h24 ?? list[idx].price_change_24h;
                    saveWatchlist(list);
                    renderWatchlistUI();
                }
            }
        }

        // Loading messages simulation
        const loadingMessages = [
            "Fetching token data...",
            "Analyzing liquidity & security...",
            "Searching X / Twitter for community buzz...",
            "Reading verified threads & sentiment...",
            "Synthesizing narrative with Gemini AI..."
        ];

        let msgInterval;

        // ================= SEARCH AUTOCOMPLETE & NAME LOOKUP =================
        const searchDropdown = document.getElementById('search-dropdown');
        const searchDropdownList = document.getElementById('search-dropdown-list');
        let searchDebounceTimer = null;
        let activeSearchItemIndex = -1;
        let currentSearchResults = [];

        function isContractAddress(str) {
            if (!str) return false;
            const s = str.trim();
            // EVM (0x followed by 40 hex chars)
            if (/^0x[a-fA-F0-9]{40}$/.test(s)) return true;
            // Solana Base58 (32 to 44 chars)
            if (/^[1-9A-HJ-NP-za-km-z]{32,44}$/.test(s)) return true;
            return false;
        }

        function hideSearchDropdown() {
            if (searchDropdown) {
                searchDropdown.style.display = 'none';
            }
            activeSearchItemIndex = -1;
        }

        function showSearchDropdown() {
            if (searchDropdown) {
                searchDropdown.style.display = 'flex';
            }
        }

        function updateActiveSearchItem() {
            const items = searchDropdownList.querySelectorAll('.search-item');
            items.forEach((el, idx) => {
                if (idx === activeSearchItemIndex) {
                    el.classList.add('active-item');
                    el.scrollIntoView({ block: 'nearest' });
                } else {
                    el.classList.remove('active-item');
                }
            });
        }

        async function triggerSearch(query) {
            const q = (query || '').trim();
            if (!q || q.length < 2) {
                hideSearchDropdown();
                return;
            }

            // If user typed exact contract address, don't show search dropdown
            if (isContractAddress(q)) {
                hideSearchDropdown();
                return;
            }

            showSearchDropdown();
            searchDropdownList.innerHTML = '<div class="search-dropdown-loading">Searching tokens across chains...</div>';

            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
                if (!res.ok) {
                    throw new Error('Search failed');
                }
                const data = await res.json();
                currentSearchResults = data.results || [];
                renderSearchDropdown(currentSearchResults, q);
            } catch (err) {
                console.error('Search error:', err);
                searchDropdownList.innerHTML = `<div class="search-dropdown-empty">Search unavailable. Try pasting contract address.</div>`;
            }
        }

        function renderSearchDropdown(results, query) {
            if (!results || results.length === 0) {
                searchDropdownList.innerHTML = `<div class="search-dropdown-empty">No tokens found for "${escapeHtml(query)}"</div>`;
                return;
            }

            let html = '';
            results.forEach((item, idx) => {
                const chainColor = getChainColor(item.chain);
                const shortAddr = shortenAddress(item.address);
                const priceStr = formatPrice(item.price_usd);
                const liqStr = item.liquidity_usd ? `${formatCompactNumber(item.liquidity_usd)} Liq` : '';
                const changeHtml = item.price_change_24h !== undefined && item.price_change_24h !== null 
                    ? formatPercent(item.price_change_24h) 
                    : '';

                const avatarHtml = item.image_url 
                    ? `<img src="${escapeHtml(item.image_url)}" alt="${escapeHtml(item.symbol)}" class="search-item-icon" onerror="this.outerHTML='<div class=\\'search-item-avatar-fallback\\'>${escapeHtml(item.symbol.slice(0, 2).toUpperCase())}</div>';">`
                    : `<div class="search-item-avatar-fallback">${escapeHtml(item.symbol.slice(0, 2).toUpperCase())}</div>`;

                html += `
                    <div class="search-item" data-index="${idx}" data-address="${escapeHtml(item.address)}">
                        <div class="search-item-left">
                            ${avatarHtml}
                            <div class="search-item-titles">
                                <div class="search-item-name-row">
                                    ${renderChainBadgeHtml(item.chain)}
                                    <span class="search-item-name">${escapeHtml(item.name)}</span>
                                    <span class="search-item-symbol">${item.pair_label ? escapeHtml(item.pair_label) : '$' + escapeHtml(item.symbol)}</span>
                                </div>
                                <div class="search-item-addr-subtext">${escapeHtml(shortAddr)}</div>
                            </div>
                        </div>
                        <div class="search-item-right">
                            <span class="search-item-price">${priceStr}</span>
                            <div class="search-item-meta">
                                ${changeHtml}
                                ${liqStr ? `<span class="search-item-liq">• ${liqStr}</span>` : ''}
                            </div>
                        </div>
                    </div>
                `;
            });

            searchDropdownList.innerHTML = html;
            activeSearchItemIndex = -1;

            // Wire click listeners on items
            searchDropdownList.querySelectorAll('.search-item').forEach(el => {
                el.addEventListener('click', () => {
                    const addr = el.getAttribute('data-address');
                    if (addr) {
                        input.value = addr;
                        hideSearchDropdown();
                        executeTokenAnalysis(addr);
                    }
                });
            });
        }

        function setupSearchAutocomplete() {
            // Live typing debounce
            input.addEventListener('input', () => {
                const val = input.value.trim();
                clearTimeout(searchDebounceTimer);
                if (!val || val.length < 2) {
                    hideSearchDropdown();
                    return;
                }
                searchDebounceTimer = setTimeout(() => {
                    triggerSearch(val);
                }, 250);
            });

            // Focus on input opens dropdown if results exist
            input.addEventListener('focus', () => {
                const val = input.value.trim();
                if (val && !isContractAddress(val) && currentSearchResults.length > 0) {
                    showSearchDropdown();
                }
            });

            // Keyboard navigation
            input.addEventListener('keydown', (e) => {
                const isDropdownOpen = searchDropdown && searchDropdown.style.display !== 'none';
                const items = searchDropdownList.querySelectorAll('.search-item');

                if (e.key === 'ArrowDown') {
                    if (!isDropdownOpen && input.value.trim().length >= 2) {
                        triggerSearch(input.value.trim());
                        return;
                    }
                    if (items.length > 0) {
                        e.preventDefault();
                        activeSearchItemIndex = (activeSearchItemIndex + 1) % items.length;
                        updateActiveSearchItem();
                    }
                } else if (e.key === 'ArrowUp') {
                    if (isDropdownOpen && items.length > 0) {
                        e.preventDefault();
                        activeSearchItemIndex = (activeSearchItemIndex - 1 + items.length) % items.length;
                        updateActiveSearchItem();
                    }
                } else if (e.key === 'Escape') {
                    hideSearchDropdown();
                } else if (e.key === 'Enter') {
                    // If a dropdown item is highlighted, select it
                    if (isDropdownOpen && activeSearchItemIndex >= 0 && items[activeSearchItemIndex]) {
                        e.preventDefault();
                        const addr = items[activeSearchItemIndex].getAttribute('data-address');
                        if (addr) {
                            input.value = addr;
                            hideSearchDropdown();
                            executeTokenAnalysis(addr);
                        }
                    } else {
                        // User pressed Enter
                        const val = input.value.trim();
                        if (!val) return;

                        if (isContractAddress(val)) {
                            // Direct contract address: analyze directly
                            hideSearchDropdown();
                        } else {
                            // Name typed and Enter pressed:
                            // Prevent blind auto-select; keep dropdown open with results so user chooses
                            e.preventDefault();
                            if (!isDropdownOpen) {
                                triggerSearch(val);
                            } else if (items.length > 0 && activeSearchItemIndex < 0) {
                                // Highlight the first item to guide the user
                                activeSearchItemIndex = 0;
                                updateActiveSearchItem();
                            }
                        }
                    }
                }
            });

            // Click outside to dismiss
            document.addEventListener('click', (e) => {
                if (!e.target.closest('.search-container')) {
                    hideSearchDropdown();
                }
            });
        }

        async function executeTokenAnalysis(contractAddress) {
            const contract = (contractAddress || input.value || '').trim();
            if (!contract) return;

            hideSearchDropdown();

            // Reset UI
            resultsArea.style.display = 'none';
            errorState.style.display = 'none';
            loadingState.style.display = 'block';
            input.disabled = true;
            btn.disabled = true;

            let msgIndex = 0;
            loadingMsg.textContent = loadingMessages[0];
            msgInterval = setInterval(() => {
                msgIndex = (msgIndex + 1) % loadingMessages.length;
                loadingMsg.textContent = loadingMessages[msgIndex];
            }, 1500);

            try {
                const res = await fetch(`/api/token/${encodeURIComponent(contract)}`);
                
                if (!res.ok) {
                    throw new Error(res.status === 404 ? "Token not found. Check contract address." : "Failed to fetch data.");
                }
                
                const data = await res.json();
                populateData(data);
                
                loadingState.style.display = 'none';
                resultsArea.style.display = 'block';
                
            } catch (err) {
                loadingState.style.display = 'none';
                errorState.style.display = 'block';
                errorMsg.textContent = err.message || "An unexpected error occurred.";
            } finally {
                clearInterval(msgInterval);
                input.disabled = false;
                btn.disabled = false;
            }
        }

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const val = input.value.trim();
            if (!val) return;

            // If it's not a contract address, trigger/keep search dropdown open so user chooses
            if (!isContractAddress(val)) {
                if (searchDropdown && searchDropdown.style.display === 'none') {
                    triggerSearch(val);
                } else {
                    const items = searchDropdownList.querySelectorAll('.search-item');
                    if (items.length > 0 && activeSearchItemIndex < 0) {
                        activeSearchItemIndex = 0;
                        updateActiveSearchItem();
                    }
                }
                return;
            }

            // Direct contract address: execute analysis
            executeTokenAnalysis(val);
        });

        function populateData(data) {
            const token = data.token;
            const narrative = data.narrative;
            const sources = data.sources;
            const tweets = data.tweets || [];

            currentContract = input.value.trim();

            // Token Info Header
            document.getElementById('token-name').textContent = token.name || 'Unknown';
            document.getElementById('token-symbol').textContent = `$${token.symbol || '???'}`;
            
            // Setup Contract Copy
            const contractToCopy = token.contract_address || currentContract || input.value.trim() || token.pair_address || '';
            setupContractCopy(contractToCopy);

            // Setup Watchlist State
            currentTokenInfo = token;
            updateWatchlistToggleBtn(isTokenInWatchlist(contractToCopy));

            const tokenImg = document.getElementById('token-image');
            if (token.image_url) {
                tokenImg.src = token.image_url;
                tokenImg.style.display = 'block';
            } else {
                tokenImg.style.display = 'none';
                tokenImg.src = '';
            }

            const chainBadge = document.getElementById('chain-badge');
            const chainInfo = getChainInfo(token.chain);
            chainBadge.innerHTML = `<img class="chain-symbol-img" src="${chainInfo.imageUrl}" alt="${escapeHtml(chainInfo.symbol)}" onerror="this.style.display='none'">`;
            chainBadge.style.backgroundColor = 'transparent';
            chainBadge.style.border = 'none';
            chainBadge.style.color = chainInfo.color;
            chainBadge.title = chainInfo.name;

            // Update live metrics
            updateMarketMetricsOnly(token);

            // Start 10-second live auto-refresh cycle
            isPaused = false;
            liveDot.classList.remove('paused');
            toggleRefreshBtn.textContent = 'Pause';
            startAutoRefreshTimer();

            // Narrative
            if (narrative) {
                setHypeBadge(narrative.hype_level);
                const confBadge = document.getElementById('confidence-badge');
                if (confBadge) {
                    confBadge.style.display = narrative.low_confidence ? 'inline-block' : 'none';
                }

                const xUpdatedText = document.getElementById('x-updated-text');
                if (xUpdatedText) {
                    if (data.last_fetched_at) {
                        xUpdatedText.textContent = `X data: ${formatRelativeTime(data.last_fetched_at)}`;
                        xUpdatedText.style.display = 'inline';
                    } else {
                        xUpdatedText.textContent = '';
                        xUpdatedText.style.display = 'none';
                    }
                }
                document.getElementById('narrative-story').textContent = narrative.story || 'No narrative available.';
                document.getElementById('sentiment-text').textContent = narrative.sentiment || 'No sentiment data.';
                
                // Buzz
                const buzzList = document.getElementById('buzz-list');
                buzzList.innerHTML = '';
                if (narrative.recent_buzz && narrative.recent_buzz.length > 0) {
                    narrative.recent_buzz.forEach(b => {
                        const li = document.createElement('li');
                        li.textContent = b;
                        buzzList.appendChild(li);
                    });
                } else {
                    buzzList.innerHTML = '<li style="color: #6b7280;">No recent buzz found.</li>';
                }

                // Risks
                const riskSection = document.getElementById('risk-section');
                const riskList = document.getElementById('risk-list');
                if (narrative.risk_signals && narrative.risk_signals.length > 0) {
                    riskSection.style.display = 'block';
                    riskList.innerHTML = '';
                    narrative.risk_signals.forEach(r => {
                        const li = document.createElement('li');
                        li.className = 'risk-item';
                        li.textContent = r;
                        riskList.appendChild(li);
                    });
                } else {
                    riskSection.style.display = 'none';
                }

                // Tags
                const tagsContainer = document.getElementById('tags-container');
                tagsContainer.innerHTML = '';
                if (narrative.tags) {
                    narrative.tags.forEach(t => {
                        const span = document.createElement('span');
                        span.className = 'tag';
                        span.textContent = t;
                        tagsContainer.appendChild(span);
                    });
                }
            }

            // Tweets Feed
            const tweetsCard = document.getElementById('tweets-card');
            const tweetsContainer = document.getElementById('tweets-container');
            const tweetCountBadge = document.getElementById('tweet-count-badge');

            if (tweets && tweets.length > 0) {
                tweetsCard.style.display = 'block';
                tweetCountBadge.textContent = `${tweets.length} tweet${tweets.length === 1 ? '' : 's'}`;
                tweetsContainer.innerHTML = '';

                tweets.forEach(t => {
                    const item = document.createElement('div');
                    item.className = 'tweet-item';

                    const verifiedSvg = t.verified 
                        ? `<svg width="14" height="14" viewBox="0 0 24 24" fill="#60a5fa" style="display:inline-block; vertical-align:middle; margin-left: 3px;"><path d="M22.5 12.5c0-1.58-.875-2.95-2.148-3.6.154-.435.238-.905.238-1.4 0-2.21-1.79-4-4-4-.495 0-.965.084-1.4.238C14.55 2.475 13.18 1.6 11.6 1.6c-1.58 0-2.95.875-3.6 2.148-.435-.154-.905-.238-1.4-.238-2.21 0-4 1.79-4 4 0 .495.084.965.238 1.4C1.475 9.55.6 10.92.6 12.5c0 1.58.875 2.95 2.148 3.6-.154.435-.238.905-.238 1.4 0 2.21 1.79 4 4 4 .495 0 .965-.084 1.4-.238 1.05 1.273 2.42 2.148 4 2.148 1.58 0 2.95-.875 3.6-2.148.435.154.905.238 1.4.238 2.21 0 4-1.79 4-4 0-.495-.084-.965-.238-1.4 1.273-1.05 2.148-2.42 2.148-4zm-12.28 4.316l-3.535-3.536 1.414-1.414 2.121 2.121 5.657-5.657 1.414 1.414-7.071 7.072z"/></svg>`
                        : '';

                    const avatarSrc = t.profile_image || `https://ui-avatars.com/api/?name=${encodeURIComponent(t.username)}&background=3b82f6&color=fff&size=64`;

                    item.innerHTML = `
                        <div class="tweet-header">
                            <div class="tweet-author-info">
                                <img src="${avatarSrc}" alt="${escapeHtml(t.username)}" class="tweet-avatar" title="Click to view profile photo" onerror="this.src='https://ui-avatars.com/api/?name=X&background=2d2d3f&color=fff';">
                                <div class="tweet-names">
                                    <div class="tweet-name">${escapeHtml(t.display_name || t.username)} ${verifiedSvg}</div>
                                    <div class="tweet-handle">@${escapeHtml(t.username)} • ${t.followers ? formatCompactNumber(t.followers) + ' followers' : ''}</div>
                                </div>
                            </div>
                        </div>
                        <div class="tweet-text">${escapeHtml(t.text)}</div>
                        <div class="tweet-footer">
                            <div class="tweet-metrics">
                                <span>❤️ ${(t.likes || 0).toLocaleString()}</span>
                                <span>🔁 ${(t.retweets || 0).toLocaleString()}</span>
                            </div>
                            ${t.url ? `<a href="${t.url}" target="_blank" class="tweet-link-btn">Open on X ↗</a>` : ''}
                        </div>
                    `;

                    // Click tweet avatar to enlarge
                    const avatarImg = item.querySelector('.tweet-avatar');
                    if (avatarImg) {
                        avatarImg.addEventListener('click', () => {
                            openImageModal(avatarSrc, `@${t.username}`, t.display_name || 'Community Member');
                        });
                    }

                    tweetsContainer.appendChild(item);
                });
            } else {
                tweetsCard.style.display = 'none';
            }

            // Sources
            const sourcesList = document.getElementById('sources-list');
            sourcesList.innerHTML = '';
            if (sources && sources.length > 0) {
                sources.forEach(s => {
                    const li = document.createElement('li');
                    const a = document.createElement('a');
                    a.href = s.url;
                    a.target = '_blank';
                    a.textContent = s.title || s.url;
                    li.appendChild(a);
                    sourcesList.appendChild(li);
                });
                document.getElementById('sources-details').style.display = 'block';
            } else {
                document.getElementById('sources-details').style.display = 'none';
            }

            // Load On-Chain Wallet Analytics (Traders & Holders)
            loadWalletAnalytics(contractToCopy, token.chain);
        }

        // Helpers
        function formatPrice(price) {
            const p = parseFloat(price);
            if (isNaN(p)) return '$0.00';
            if (p === 0) return '$0.00';
            if (p < 0.000001) return '$' + p.toExponential(4);
            if (p < 0.0001) return '$' + p.toFixed(8);
            if (p < 0.01) return '$' + p.toFixed(6);
            if (p < 1) return '$' + p.toFixed(4);
            return '$' + p.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        }

        function formatCompactNumber(number) {
            const n = parseFloat(number);
            if (isNaN(n)) return '-';
            if (n >= 1e9) return '$' + (n / 1e9).toFixed(2) + 'B';
            if (n >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
            if (n >= 1e3) return '$' + (n / 1e3).toFixed(1) + 'K';
            return '$' + n.toFixed(2);
        }

        function formatTokenSupply(amount) {
            const n = parseFloat(amount);
            if (isNaN(n) || n <= 0) return '-';
            if (n >= 1e12) return (n / 1e12).toFixed(2) + 'T';
            if (n >= 1e9) return (n / 1e9).toFixed(2) + 'B';
            if (n >= 1e6) return (n / 1e6).toFixed(2) + 'M';
            if (n >= 1e3) return (n / 1e3).toFixed(2) + 'K';
            return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
        }

        function formatPercent(val) {
            const p = parseFloat(val);
            if (isNaN(p)) return '-';
            const isPos = p > 0;
            const isZero = p === 0;
            const sign = isPos ? '+' : '';
            const colorClass = isZero ? '' : (isPos ? 'positive' : 'negative');
            return `<span class="${colorClass}">${sign}${p.toFixed(2)}%</span>`;
        }

        function formatRelativeTime(dateStr) {
            if (!dateStr) return 'recently';
            if (typeof dateStr === 'string' && (dateStr.toLowerCase().includes('just') || dateStr.toLowerCase().includes('now'))) {
                return 'Just now';
            }
            const date = new Date(dateStr);
            if (isNaN(date.getTime())) return 'recently';
            const now = new Date();
            const diffInSeconds = Math.floor((now - date) / 1000);
            
            if (diffInSeconds < 0 || diffInSeconds < 60) return 'Just now';
            if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
            if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
            return `${Math.floor(diffInSeconds / 86400)}d ago`;
        }

        function setHypeBadge(level) {
            const badge = document.getElementById('hype-badge');
            badge.className = 'hype-badge';
            const l = (level || '').toLowerCase();
            
            if (l.includes('extreme')) {
                badge.classList.add('hype-extreme');
                badge.textContent = 'Extreme 🔥';
            } else if (l.includes('high')) {
                badge.classList.add('hype-high');
                badge.textContent = 'High 🚀';
            } else if (l.includes('low')) {
                badge.classList.add('hype-low');
                badge.textContent = 'Low 😴';
            } else {
                badge.classList.add('hype-medium');
                badge.textContent = 'Medium ⚡';
            }
        }

        function getChainColor(chain) {
            const c = (chain || '').toLowerCase();
            if (c.includes('solana')) return 'var(--chain-solana)';
            if (c.includes('ethereum') || c === 'eth') return 'var(--chain-eth)';
            if (c.includes('base')) return 'var(--chain-base)';
            if (c.includes('bsc') || c.includes('binance')) return 'var(--chain-bsc)';
            if (c.includes('robinhood')) return '#00c805';
            if (c.includes('ink')) return '#7c3aed';
            if (c.includes('arbitrum')) return '#28a0f0';
            if (c.includes('polygon')) return '#8247e5';
            return 'var(--chain-default)';
        }

        function escapeHtml(str) {
            if (!str) return '';
            return str
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        // ================= ON-CHAIN WALLET ANALYTICS JS =================
        let activeWalletTab = 'traders';
        let currentWalletContract = null;
        let currentWalletChain = null;

        const CHAIN_EXPLORER_BASE = {
            solana: 'https://solscan.io/account/',
            ethereum: 'https://etherscan.io/address/',
            eth: 'https://etherscan.io/address/',
            base: 'https://basescan.org/address/',
            bsc: 'https://bscscan.com/address/',
            binance: 'https://bscscan.com/address/',
            arbitrum: 'https://arbiscan.io/address/',
            polygon: 'https://polygonscan.com/address/',
            robinhood: 'https://robinhoodchain.blockscout.com/address/',
            ink: 'https://explorer.inkonchain.com/address/'
        };

        function getWalletExplorerUrl(chain, wallet) {
            const c = (chain || '').toLowerCase();
            for (const key in CHAIN_EXPLORER_BASE) {
                if (c.includes(key)) {
                    return `${CHAIN_EXPLORER_BASE[key]}${wallet}`;
                }
            }
            return `https://blockscan.com/address/${wallet}`;
        }

        function shortenAddress(addr) {
            if (!addr) return '';
            if (addr.length <= 12) return addr;
            return `${addr.slice(0, 5)}...${addr.slice(-4)}`;
        }

        function copyWalletAddress(wallet, btn) {
            if (!wallet) return;
            const handleSuccess = () => {
                const orig = btn.textContent;
                btn.textContent = '✓';
                btn.style.color = '#10b981';
                setTimeout(() => {
                    btn.textContent = orig;
                    btn.style.color = '';
                }, 1500);
            };

            if (navigator.clipboard && window.isSecureContext) {
                navigator.clipboard.writeText(wallet).then(handleSuccess).catch(() => {
                    if (fallbackCopyText(wallet)) handleSuccess();
                });
            } else {
                if (fallbackCopyText(wallet)) handleSuccess();
            }
        }

        function switchWalletTab(tab) {
            activeWalletTab = tab;
            const tabBtnTraders = document.getElementById('tab-btn-traders');
            const tabBtnHolders = document.getElementById('tab-btn-holders');
            const tabContentTraders = document.getElementById('tab-content-traders');
            const tabContentHolders = document.getElementById('tab-content-holders');
            const tabInfo = document.getElementById('wallet-tab-info');

            if (tab === 'traders') {
                tabBtnTraders.classList.add('active');
                tabBtnHolders.classList.remove('active');
                tabContentTraders.style.display = 'block';
                tabContentHolders.style.display = 'none';
                if (tabInfo) tabInfo.textContent = 'Direct on-chain DEX swap execution analysis';
            } else {
                tabBtnHolders.classList.add('active');
                tabBtnTraders.classList.remove('active');
                tabContentHolders.style.display = 'block';
                tabContentTraders.style.display = 'none';
                if (tabInfo) {
                    const c = (currentWalletChain || '').toLowerCase();
                    tabInfo.textContent = c.includes('solana')
                        ? 'Direct Solana RPC (getTokenLargestAccounts)'
                        : 'On-chain Transfer event log balance aggregation';
                }
            }
        }

        async function loadWalletAnalytics(contract, chain, forceRefresh = false) {
            if (!contract) return;
            currentWalletContract = contract;
            currentWalletChain = chain;

            const card = document.getElementById('wallet-analytics-card');
            if (card) card.style.display = 'block';

            const chainBadge = document.getElementById('wallet-chain-badge');
            if (chainBadge && chain) {
                chainBadge.textContent = `${chain.toUpperCase()} RPC`;
            }

            const refreshBtn = document.getElementById('refresh-wallets-btn');
            const refreshBtnText = document.getElementById('refresh-wallets-btn-text');
            const updatedText = document.getElementById('wallet-updated-text');
            const tradersBody = document.getElementById('traders-table-body');
            const holdersBody = document.getElementById('holders-table-body');

            if (forceRefresh) {
                if (refreshBtn) refreshBtn.disabled = true;
                if (refreshBtnText) refreshBtnText.textContent = 'Scanning RPC...';
            }

            if (forceRefresh || !tradersBody.querySelector('tr[data-loaded="true"]')) {
                tradersBody.innerHTML = '<tr><td colspan="6" class="wallet-loading-cell">Scanning on-chain DEX swap events...</td></tr>';
            }
            if (forceRefresh || !holdersBody.querySelector('tr[data-loaded="true"]')) {
                holdersBody.innerHTML = '<tr><td colspan="6" class="wallet-loading-cell">Querying blockchain token holders...</td></tr>';
            }

            try {
                const refreshParam = forceRefresh ? '?refresh=true' : '';
                
                // Fetch Traders and Holders concurrently
                const [tradersRes, holdersRes] = await Promise.allSettled([
                    fetch(`/api/token/${encodeURIComponent(contract)}/traders${refreshParam}`),
                    fetch(`/api/token/${encodeURIComponent(contract)}/holders${refreshParam}`)
                ]);

                // Render Traders
                if (tradersRes.status === 'fulfilled' && tradersRes.value.ok) {
                    const data = await tradersRes.value.json();
                    renderTradersTable(data.traders || [], chain);
                    if (data.fetched_at && updatedText) {
                        updatedText.textContent = `On-chain: ${formatRelativeTime(data.fetched_at)}`;
                    }
                } else {
                    tradersBody.innerHTML = '<tr><td colspan="6" class="wallet-empty-cell">No recent DEX swap trades found on-chain.</td></tr>';
                }

                // Render Holders
                if (holdersRes.status === 'fulfilled' && holdersRes.value.ok) {
                    const data = await holdersRes.value.json();
                    renderHoldersTable(data.holders || [], chain, data);
                } else {
                    holdersBody.innerHTML = '<tr><td colspan="6" class="wallet-empty-cell">No on-chain holder balances found.</td></tr>';
                    const summaryBar = document.getElementById('holders-summary-bar');
                    if (summaryBar) summaryBar.style.display = 'none';
                }

                if (forceRefresh && refreshBtnText) {
                    refreshBtnText.textContent = 'Updated! ✓';
                    setTimeout(() => {
                        if (refreshBtnText) refreshBtnText.textContent = 'Refresh On-Chain';
                    }, 2000);
                }
            } catch (err) {
                console.error('Failed to load wallet analytics:', err);
                if (refreshBtnText) refreshBtnText.textContent = 'Refresh On-Chain';
            } finally {
                if (refreshBtn) refreshBtn.disabled = false;
            }
        }

        function renderTradersTable(traders, chain) {
            const body = document.getElementById('traders-table-body');
            if (!body) return;

            if (!traders || traders.length === 0) {
                body.innerHTML = '<tr><td colspan="6" class="wallet-empty-cell">No recent trader activity detected on-chain.</td></tr>';
                return;
            }

            let html = '';
            traders.forEach((t, i) => {
                const rank = t.rank || (i + 1);
                const rankClass = rank === 1 ? 'wallet-rank-1' : (rank === 2 ? 'wallet-rank-2' : (rank === 3 ? 'wallet-rank-3' : ''));
                const wallet = t.wallet_address || '';
                const shortAddr = shortenAddress(wallet);
                const explorerUrl = getWalletExplorerUrl(chain, wallet);
                const volumeStr = `$${(t.total_volume_usd || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                
                const pnl = t.estimated_pnl_usd || 0;
                const pnlPct = t.estimated_pnl_pct || 0;
                const isPos = pnl > 0;
                const isNeg = pnl < 0;
                const pnlClass = isPos ? 'pnl-badge-pos' : (isNeg ? 'pnl-badge-neg' : '');
                const pnlSign = isPos ? '+' : (isNeg ? '-' : '');
                const pnlStr = `${pnlSign}$${Math.abs(pnl).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                const pnlPctStr = `${pnlSign}${Math.abs(pnlPct).toFixed(1)}%`;

                html += `
                    <tr data-loaded="true">
                        <td>
                            <span class="wallet-rank-badge ${rankClass}">${rank}</span>
                        </td>
                        <td>
                            <div class="wallet-addr-wrapper">
                                <span title="${escapeHtml(wallet)}">${escapeHtml(shortAddr)}</span>
                                <button type="button" class="wallet-action-btn" title="Copy wallet address" onclick="copyWalletAddress('${escapeHtml(wallet)}', this)">📋</button>
                            </div>
                        </td>
                        <td style="font-weight: 600; font-variant-numeric: tabular-nums;">${volumeStr}</td>
                        <td style="font-variant-numeric: tabular-nums;">
                            <span class="tx-pill-buy">${t.buy_count || 0}B</span>
                            <span style="color: #6b7280;"> / </span>
                            <span class="tx-pill-sell">${t.sell_count || 0}S</span>
                        </td>
                        <td>
                            <div class="${pnlClass}" style="font-variant-numeric: tabular-nums;">
                                <span>${pnlStr}</span>
                                <span class="pnl-subtext">${pnlPctStr}</span>
                            </div>
                        </td>
                        <td style="text-align: right;">
                            <a href="${explorerUrl}" target="_blank" rel="noopener noreferrer" class="wallet-action-btn" title="View on Block Explorer">↗</a>
                        </td>
                    </tr>
                `;
            });

            body.innerHTML = html;
        }

        function renderHoldersTable(holders, chain, summaryData) {
            const body = document.getElementById('holders-table-body');
            const summaryBar = document.getElementById('holders-summary-bar');
            const summarySupply = document.getElementById('summary-total-supply');
            const summaryHolders = document.getElementById('summary-total-holders');
            const summarySupplyHeldPct = document.getElementById('summary-supply-held-pct');
            const summarySupplyBar = document.getElementById('summary-supply-bar');

            // Render summary stat bar if summaryData is present
            if (summaryData && (summaryData.total_supply || summaryData.total_holders || summaryData.total_supply_held)) {
                if (summaryBar) summaryBar.style.display = 'flex';

                const supply = summaryData.total_supply;
                if (summarySupply) {
                    if (supply) {
                        summarySupply.textContent = formatTokenSupply(supply);
                        summarySupply.title = `Exact on-chain: ${Number(supply).toLocaleString()} tokens`;
                        // Also sync to market metrics tile
                        const mmetricsSupply = document.getElementById('total-supply');
                        if (mmetricsSupply && (mmetricsSupply.textContent === '-' || mmetricsSupply.textContent === '--')) {
                            mmetricsSupply.textContent = formatTokenSupply(supply);
                            mmetricsSupply.title = `${Number(supply).toLocaleString()} tokens`;
                        }
                    } else {
                        summarySupply.textContent = 'Unknown';
                    }
                }

                if (summaryHolders) {
                    const count = summaryData.total_holders || (holders ? holders.length : 0);
                    summaryHolders.textContent = count ? `${count.toLocaleString()}+ Wallets` : '0';
                }

                const heldPct = summaryData.total_supply_held_pct || 0;
                const heldAmount = summaryData.total_supply_held;
                if (summarySupplyHeldPct) {
                    if (heldAmount && supply) {
                        summarySupplyHeldPct.textContent = `${heldPct.toFixed(2)}% (${formatTokenSupply(heldAmount)})`;
                    } else {
                        summarySupplyHeldPct.textContent = `${heldPct.toFixed(2)}%`;
                    }
                }
                if (summarySupplyBar) {
                    summarySupplyBar.style.width = `${Math.min(100, Math.max(0, heldPct))}%`;
                }
            } else {
                if (summaryBar) summaryBar.style.display = 'none';
            }

            if (!body) return;

            if (!holders || holders.length === 0) {
                body.innerHTML = '<tr><td colspan="6" class="wallet-empty-cell">No on-chain holder accounts identified.</td></tr>';
                return;
            }

            let html = '';
            holders.forEach((h, i) => {
                const rank = h.rank || (i + 1);
                const rankClass = rank === 1 ? 'wallet-rank-1' : (rank === 2 ? 'wallet-rank-2' : (rank === 3 ? 'wallet-rank-3' : ''));
                const wallet = h.wallet_address || '';
                const shortAddr = shortenAddress(wallet);
                const explorerUrl = getWalletExplorerUrl(chain, wallet);
                const balanceStr = typeof h.balance === 'number' ? h.balance.toLocaleString() : (h.balance || '0');
                const pct = Math.min(100, Math.max(0, h.percentage || 0));
                const valueStr = h.value_usd ? `$${h.value_usd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : '-';

                html += `
                    <tr data-loaded="true">
                        <td>
                            <span class="wallet-rank-badge ${rankClass}">${rank}</span>
                        </td>
                        <td>
                            <div class="wallet-addr-wrapper">
                                <span title="${escapeHtml(wallet)}">${escapeHtml(shortAddr)}</span>
                                <button type="button" class="wallet-action-btn" title="Copy wallet address" onclick="copyWalletAddress('${escapeHtml(wallet)}', this)">📋</button>
                            </div>
                        </td>
                        <td style="font-variant-numeric: tabular-nums; font-weight: 500;">${balanceStr}</td>
                        <td>
                            <div style="display: flex; justify-content: space-between; font-size: 0.8rem; font-variant-numeric: tabular-nums;">
                                <span style="font-weight: 600;">${pct.toFixed(2)}%</span>
                            </div>
                            <div class="supply-bar-container">
                                <div class="supply-bar-fill" style="width: ${pct}%;"></div>
                            </div>
                        </td>
                        <td style="font-variant-numeric: tabular-nums; font-weight: 600;">${valueStr}</td>
                        <td style="text-align: right;">
                            <a href="${explorerUrl}" target="_blank" rel="noopener noreferrer" class="wallet-action-btn" title="View on Block Explorer">↗</a>
                        </td>
                    </tr>
                `;
            });

            body.innerHTML = html;
        }

        // Wire Refresh Wallets Button & Tabs
        document.getElementById('refresh-wallets-btn')?.addEventListener('click', () => {
            if (currentWalletContract) {
                loadWalletAnalytics(currentWalletContract, currentWalletChain, true);
            }
        });

        document.getElementById('tab-btn-traders')?.addEventListener('click', () => switchWalletTab('traders'));
        document.getElementById('tab-btn-holders')?.addEventListener('click', () => switchWalletTab('holders'));

        // Initialize Search Autocomplete
        setupSearchAutocomplete();
