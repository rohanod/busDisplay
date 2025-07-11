/**
 * Bus Display Web UI - Main Application JavaScript
 * Handles all interactivity, API calls, and dynamic functionality
 */

class BusDisplayUI {
    constructor() {
        this.config = {};
        this.selectedStop = null;
        this.searchTimeout = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadInitialData();
        this.startStatusPolling();
    }

    setupEventListeners() {
        // Tab navigation
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Restart button
        document.getElementById('restartBtn').addEventListener('click', () => this.restartService());
        document.getElementById('restartServiceBtn').addEventListener('click', () => this.restartService());

        // Stop management
        document.getElementById('addStopBtn').addEventListener('click', () => this.showAddStopModal());
        document.getElementById('closeAddStopModal').addEventListener('click', () => this.hideAddStopModal());
        document.getElementById('cancelAddStop').addEventListener('click', () => this.hideAddStopModal());
        document.getElementById('confirmAddStop').addEventListener('click', () => this.addStop());

        // Stop search
        document.getElementById('newStopSearch').addEventListener('input', (e) => this.searchStops(e.target.value, 'newStopResults'));

        // Filter type radio buttons
        document.querySelectorAll('input[name="filterType"]').forEach(radio => {
            radio.addEventListener('change', () => this.updateFilterConfig());
        });

        // Settings
        document.getElementById('saveDisplaySettings').addEventListener('click', () => this.saveDisplaySettings());

        // Advanced features
        document.getElementById('exportConfigBtn').addEventListener('click', () => this.exportConfig());
        document.getElementById('importConfigBtn').addEventListener('click', () => document.getElementById('importFileInput').click());
        document.getElementById('importFileInput').addEventListener('change', (e) => this.importConfig(e));

        // Modal backdrop clicks
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideModal(modal);
                }
            });
        });

        // Escape key to close modals
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                document.querySelectorAll('.modal.show').forEach(modal => {
                    this.hideModal(modal);
                });
            }
        });
    }

    async loadInitialData() {
        try {
            await this.loadConfig();
            await this.loadStatus();
            await this.loadBackups();
            this.updateUI();
        } catch (error) {
            this.showToast('Failed to load initial data', 'error');
            console.error('Failed to load initial data:', error);
        }
    }

    async loadConfig() {
        try {
            const response = await fetch('/api/config');
            if (!response.ok) throw new Error('Failed to load configuration');
            this.config = await response.json();
        } catch (error) {
            console.error('Error loading config:', error);
            throw error;
        }
    }

    async saveConfig() {
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(this.config)
            });
            
            const result = await response.json();
            if (!result.success) {
                throw new Error(result.message);
            }
            
            this.showToast('Configuration saved successfully', 'success');
            return true;
        } catch (error) {
            this.showToast('Failed to save configuration: ' + error.message, 'error');
            console.error('Error saving config:', error);
            return false;
        }
    }

    async loadStatus() {
        try {
            const response = await fetch('/api/status');
            if (!response.ok) throw new Error('Failed to load status');
            this.status = await response.json();
        } catch (error) {
            console.error('Error loading status:', error);
            this.status = { service_status: 'unknown', config_exists: false };
        }
    }

    async loadBackups() {
        try {
            const response = await fetch('/api/backups');
            if (!response.ok) throw new Error('Failed to load backups');
            this.backups = await response.json();
        } catch (error) {
            console.error('Error loading backups:', error);
            this.backups = [];
        }
    }

    updateUI() {
        this.updateStatusIndicator();
        this.updateDashboard();
        this.updateStopsList();
        this.updateDisplaySettings();
        this.updateBackupsList();
    }

    updateStatusIndicator() {
        const indicator = document.getElementById('serviceStatus');
        const statusText = document.getElementById('serviceStatusText');
        
        indicator.className = 'status-indicator';
        
        switch (this.status.service_status) {
            case 'active':
                indicator.classList.add('active');
                indicator.innerHTML = '<i class="fas fa-circle"></i><span>Active</span>';
                if (statusText) statusText.textContent = 'Active';
                break;
            case 'inactive':
                indicator.classList.add('inactive');
                indicator.innerHTML = '<i class="fas fa-circle"></i><span>Inactive</span>';
                if (statusText) statusText.textContent = 'Inactive';
                break;
            default:
                indicator.classList.add('unknown');
                indicator.innerHTML = '<i class="fas fa-circle"></i><span>Unknown</span>';
                if (statusText) statusText.textContent = 'Unknown';
        }
    }

    updateDashboard() {
        // Update config status
        const configStatus = document.getElementById('configStatus');
        if (configStatus) {
            configStatus.textContent = this.status.config_exists ? 'Found' : 'Missing';
        }

        // Update stops count
        const stopsCount = document.getElementById('stopsCount');
        if (stopsCount) {
            stopsCount.textContent = this.config.stops ? this.config.stops.length : 0;
        }

        // Update last updated
        const lastUpdated = document.getElementById('lastUpdated');
        if (lastUpdated && this.status.timestamp) {
            const date = new Date(this.status.timestamp);
            lastUpdated.textContent = date.toLocaleString();
        }

        // Update quick stats
        const fetchInterval = document.getElementById('fetchInterval');
        const maxDepartures = document.getElementById('maxDepartures');
        const maxMinutes = document.getElementById('maxMinutes');
        
        if (fetchInterval) fetchInterval.textContent = this.config.fetch_interval || 60;
        if (maxDepartures) maxDepartures.textContent = this.config.max_departures || 8;
        if (maxMinutes) maxMinutes.textContent = this.config.max_minutes || 120;
    }

    updateStopsList() {
        const stopsList = document.getElementById('stopsList');
        if (!stopsList) return;

        if (!this.config.stops || this.config.stops.length === 0) {
            stopsList.innerHTML = `
                <div class="card">
                    <div class="card-body text-center">
                        <i class="fas fa-map-marker-alt" style="font-size: 3rem; color: var(--text-secondary); margin-bottom: 1rem;"></i>
                        <h3>No stops configured</h3>
                        <p style="color: var(--text-secondary);">Click "Add Stop" to get started</p>
                    </div>
                </div>
            `;
            return;
        }

        stopsList.innerHTML = this.config.stops.map((stop, index) => `
            <div class="stop-card" data-index="${index}">
                <div class="stop-card-header">
                    <div>
                        <div class="stop-name">${this.getStopDisplayName(stop)}</div>
                        <div class="stop-id">ID: ${stop.ID}</div>
                    </div>
                    <div class="stop-actions">
                        <button class="btn btn-secondary btn-sm" onclick="app.editStop(${index})">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="app.removeStop(${index})">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                ${this.renderStopFilters(stop)}
            </div>
        `).join('');
    }

    getStopDisplayName(stop) {
        // If we have cached stop info, use the name from there
        if (stop._cached_name) {
            return stop._cached_name;
        }
        return `Stop ${stop.ID}`;
    }

    renderStopFilters(stop) {
        let filtersHtml = '';
        
        if (stop.LinesInclude) {
            const lines = Object.keys(stop.LinesInclude);
            filtersHtml = `
                <div class="stop-lines">
                    <strong>Including lines:</strong>
                    ${lines.map(line => `<span class="line-badge">${line}</span>`).join('')}
                </div>
            `;
        } else if (stop.LinesExclude) {
            const lines = Object.keys(stop.LinesExclude);
            filtersHtml = `
                <div class="stop-lines">
                    <strong>Excluding lines:</strong>
                    ${lines.map(line => `<span class="line-badge" style="background: var(--error-red);">${line}</span>`).join('')}
                </div>
            `;
        }
        
        return filtersHtml;
    }

    updateDisplaySettings() {
        // Update form fields with current config values
        const fields = [
            'fetchIntervalInput', 'maxDeparturesInput', 'maxMinutesInput', 'httpTimeoutInput',
            'showClockInput', 'showWeatherInput', 'colsInput', 'rowsInput'
        ];

        fields.forEach(fieldId => {
            const field = document.getElementById(fieldId);
            if (!field) return;

            const configKey = fieldId.replace('Input', '').replace(/([A-Z])/g, '_$1').toLowerCase();
            
            if (field.type === 'checkbox') {
                field.checked = this.config[configKey] !== false;
            } else {
                field.value = this.config[configKey] || field.defaultValue || '';
            }
        });
    }

    updateBackupsList() {
        const backupList = document.getElementById('backupList');
        const recentBackups = document.getElementById('recentBackups');
        
        if (!this.backups || this.backups.length === 0) {
            const noBackupsHtml = '<p style="color: var(--text-secondary);">No backups available</p>';
            if (backupList) backupList.innerHTML = noBackupsHtml;
            if (recentBackups) recentBackups.innerHTML = noBackupsHtml;
            return;
        }

        const backupsHtml = this.backups.slice(0, 5).map(backup => {
            const date = new Date(backup.timestamp);
            return `
                <div class="backup-item" style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid rgba(255,255,255,0.1);">
                    <div>
                        <div style="font-weight: 500;">${backup.filename}</div>
                        <div style="font-size: 0.75rem; color: var(--text-secondary);">${date.toLocaleString()}</div>
                    </div>
                    <a href="/api/backups/${backup.filename}" class="btn btn-secondary btn-sm">
                        <i class="fas fa-download"></i>
                    </a>
                </div>
            `;
        }).join('');

        if (backupList) backupList.innerHTML = backupsHtml;
        if (recentBackups) recentBackups.innerHTML = backupsHtml;
    }

    switchTab(tabName) {
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.toggle('active', content.id === tabName);
        });
    }

    async restartService() {
        const btn = document.getElementById('restartBtn');
        const originalText = btn.innerHTML;
        
        try {
            btn.innerHTML = '<i class="spinner"></i> Restarting...';
            btn.disabled = true;

            const response = await fetch('/api/restart', { method: 'POST' });
            const result = await response.json();

            if (result.success) {
                this.showToast('Service restarted successfully', 'success');
                // Refresh status after a delay
                setTimeout(() => this.loadStatus().then(() => this.updateStatusIndicator()), 2000);
            } else {
                throw new Error(result.message);
            }
        } catch (error) {
            this.showToast('Failed to restart service: ' + error.message, 'error');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }

    async searchStops(query, resultsElementId) {
        if (this.searchTimeout) {
            clearTimeout(this.searchTimeout);
        }

        const resultsElement = document.getElementById(resultsElementId);
        if (!resultsElement) return;

        if (!query.trim()) {
            resultsElement.classList.remove('show');
            return;
        }

        this.searchTimeout = setTimeout(async () => {
            try {
                const response = await fetch(`/api/search/stops?q=${encodeURIComponent(query)}`);
                const stops = await response.json();

                if (stops.length === 0) {
                    resultsElement.innerHTML = '<div class="search-result-item">No stops found</div>';
                } else {
                    resultsElement.innerHTML = stops.map(stop => `
                        <div class="search-result-item" data-stop-id="${stop.id}" data-stop-name="${stop.name}">
                            <strong>${stop.name}</strong>
                            <div style="font-size: 0.875rem; color: var(--text-secondary);">ID: ${stop.id}</div>
                        </div>
                    `).join('');

                    // Add click handlers
                    resultsElement.querySelectorAll('.search-result-item').forEach(item => {
                        item.addEventListener('click', () => this.selectStop(item.dataset.stopId, item.dataset.stopName));
                    });
                }

                resultsElement.classList.add('show');
            } catch (error) {
                console.error('Search error:', error);
                resultsElement.innerHTML = '<div class="search-result-item">Search failed</div>';
                resultsElement.classList.add('show');
            }
        }, 300);
    }

    async selectStop(stopId, stopName) {
        try {
            // Hide search results
            document.getElementById('newStopResults').classList.remove('show');
            
            // Clear search input
            document.getElementById('newStopSearch').value = stopName;
            
            // Load stop information
            const response = await fetch(`/api/stops/${stopId}/info`);
            const stopInfo = await response.json();

            if (stopInfo.error) {
                throw new Error(stopInfo.error);
            }

            this.selectedStop = stopInfo;
            this.showStopInfo();
            
        } catch (error) {
            this.showToast('Failed to load stop information: ' + error.message, 'error');
        }
    }

    showStopInfo() {
        const infoElement = document.getElementById('selectedStopInfo');
        const contentElement = document.getElementById('stopInfoContent');
        
        if (!this.selectedStop) return;

        contentElement.innerHTML = `
            <div style="margin-bottom: 1rem;">
                <strong>Name:</strong> ${this.selectedStop.name}<br>
                <strong>ID:</strong> ${this.selectedStop.id}<br>
                <strong>Available Lines:</strong> ${this.selectedStop.lines.join(', ')}
            </div>
        `;

        infoElement.style.display = 'block';
        document.getElementById('confirmAddStop').disabled = false;
        
        this.updateFilterConfig();
    }

    updateFilterConfig() {
        const filterType = document.querySelector('input[name="filterType"]:checked').value;
        const configElement = document.getElementById('lineFilterConfig');
        
        if (filterType === 'none') {
            configElement.style.display = 'none';
            return;
        }

        if (!this.selectedStop) {
            configElement.style.display = 'none';
            return;
        }

        const lines = this.selectedStop.lines;
        const terminals = this.selectedStop.terminals;

        configElement.innerHTML = `
            <div style="margin-top: 1rem;">
                <label>Select lines to ${filterType}:</label>
                ${lines.map(line => `
                    <div style="margin: 0.5rem 0;">
                        <label class="checkbox-label">
                            <input type="checkbox" name="selectedLines" value="${line}">
                            <span>Line ${line}</span>
                        </label>
                        ${terminals[line] && terminals[line].length > 1 ? `
                            <select name="terminal_${line}" style="margin-left: 1.5rem; margin-top: 0.25rem;" disabled>
                                <option value="">Any destination</option>
                                ${terminals[line].map(terminal => `
                                    <option value="${terminal.id}">${terminal.name}</option>
                                `).join('')}
                            </select>
                        ` : ''}
                    </div>
                `).join('')}
            </div>
        `;

        // Enable/disable terminal selects based on line selection
        configElement.querySelectorAll('input[name="selectedLines"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                const terminalSelect = configElement.querySelector(`select[name="terminal_${checkbox.value}"]`);
                if (terminalSelect) {
                    terminalSelect.disabled = !checkbox.checked;
                    if (!checkbox.checked) {
                        terminalSelect.value = '';
                    }
                }
            });
        });

        configElement.style.display = 'block';
    }

    showAddStopModal() {
        document.getElementById('addStopModal').classList.add('show');
        document.getElementById('newStopSearch').focus();
    }

    hideAddStopModal() {
        document.getElementById('addStopModal').classList.remove('show');
        this.resetAddStopModal();
    }

    resetAddStopModal() {
        document.getElementById('newStopSearch').value = '';
        document.getElementById('newStopResults').classList.remove('show');
        document.getElementById('selectedStopInfo').style.display = 'none';
        document.getElementById('confirmAddStop').disabled = true;
        document.querySelector('input[name="filterType"][value="none"]').checked = true;
        this.selectedStop = null;
    }

    async addStop() {
        if (!this.selectedStop) return;

        const filterType = document.querySelector('input[name="filterType"]:checked').value;
        const newStop = {
            ID: this.selectedStop.id,
            _cached_name: this.selectedStop.name
        };

        if (filterType !== 'none') {
            const selectedLines = Array.from(document.querySelectorAll('input[name="selectedLines"]:checked'))
                .map(cb => cb.value);

            if (selectedLines.length === 0) {
                this.showToast('Please select at least one line to filter', 'warning');
                return;
            }

            const filterConfig = {};
            selectedLines.forEach(line => {
                const terminalSelect = document.querySelector(`select[name="terminal_${line}"]`);
                const terminalId = terminalSelect ? terminalSelect.value : null;
                filterConfig[line] = terminalId || null;
            });

            if (filterType === 'include') {
                newStop.LinesInclude = filterConfig;
            } else {
                newStop.LinesExclude = filterConfig;
            }
        }

        // Add to config
        if (!this.config.stops) {
            this.config.stops = [];
        }
        this.config.stops.push(newStop);

        // Save and update UI
        if (await this.saveConfig()) {
            this.updateStopsList();
            this.updateDashboard();
            this.hideAddStopModal();
            this.showToast('Stop added successfully', 'success');
        }
    }

    removeStop(index) {
        if (confirm('Are you sure you want to remove this stop?')) {
            this.config.stops.splice(index, 1);
            this.saveConfig().then(() => {
                this.updateStopsList();
                this.updateDashboard();
                this.showToast('Stop removed successfully', 'success');
            });
        }
    }

    editStop(index) {
        // For now, just show a simple prompt to edit the stop
        // In a full implementation, you'd want a proper edit modal
        this.showToast('Edit functionality coming soon', 'info');
    }

    async saveDisplaySettings() {
        const btn = document.getElementById('saveDisplaySettings');
        const originalText = btn.innerHTML;
        
        try {
            btn.innerHTML = '<i class="spinner"></i> Saving...';
            btn.disabled = true;

            // Collect form values
            const settings = {
                fetch_interval: parseInt(document.getElementById('fetchIntervalInput').value),
                max_departures: parseInt(document.getElementById('maxDeparturesInput').value),
                max_minutes: parseInt(document.getElementById('maxMinutesInput').value),
                http_timeout: parseInt(document.getElementById('httpTimeoutInput').value),
                show_clock: document.getElementById('showClockInput').checked,
                show_weather: document.getElementById('showWeatherInput').checked,
                cols: parseInt(document.getElementById('colsInput').value),
                rows: parseInt(document.getElementById('rowsInput').value)
            };

            // Update config
            Object.assign(this.config, settings);

            // Save
            if (await this.saveConfig()) {
                this.updateDashboard();
                this.showToast('Display settings saved successfully', 'success');
            }
        } catch (error) {
            this.showToast('Failed to save settings: ' + error.message, 'error');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    }

    exportConfig() {
        const dataStr = JSON.stringify(this.config, null, 2);
        const dataBlob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(dataBlob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = `busdisplay_config_${new Date().toISOString().split('T')[0]}.json`;
        link.click();
        
        URL.revokeObjectURL(url);
        this.showToast('Configuration exported successfully', 'success');
    }

    importConfig(event) {
        const file = event.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = async (e) => {
            try {
                const importedConfig = JSON.parse(e.target.result);
                
                if (confirm('This will replace your current configuration. Are you sure?')) {
                    this.config = importedConfig;
                    if (await this.saveConfig()) {
                        this.updateUI();
                        this.showToast('Configuration imported successfully', 'success');
                    }
                }
            } catch (error) {
                this.showToast('Failed to import configuration: Invalid file format', 'error');
            }
        };
        reader.readAsText(file);
        
        // Reset file input
        event.target.value = '';
    }

    hideModal(modal) {
        modal.classList.remove('show');
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = {
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle',
            info: 'fas fa-info-circle'
        }[type] || 'fas fa-info-circle';
        
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <i class="${icon}"></i>
                <span>${message}</span>
            </div>
        `;
        
        container.appendChild(toast);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 5000);
        
        // Click to dismiss
        toast.addEventListener('click', () => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        });
    }

    startStatusPolling() {
        // Poll status every 30 seconds
        setInterval(async () => {
            await this.loadStatus();
            this.updateStatusIndicator();
        }, 30000);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.app = new BusDisplayUI();
});