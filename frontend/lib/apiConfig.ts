interface APIConfig {
  baseUrl: string;
  name: string;
  isActive: boolean;
  lastUsed?: Date;
}

class APIConfigManager {
  private static instance: APIConfigManager;
  private configs: APIConfig[] = [];
  private activeConfig: APIConfig | null = null;
  private readonly storageKey: string = 'api_config';

  private constructor() {
    this.loadConfigs();
  }

  static getInstance(): APIConfigManager {
    if (!APIConfigManager.instance) {
      APIConfigManager.instance = new APIConfigManager();
    }
    return APIConfigManager.instance;
  }

  private loadConfigs() {
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(this.storageKey);
      if (stored) {
        try {
          this.configs = JSON.parse(stored);
          this.activeConfig = this.configs.find(c => c.isActive) || null;
        } catch (error) {
          console.error('Error loading API configs:', error);
          this.configs = [];
          this.activeConfig = null;
        }
      }
    }
  }

  private saveConfigs() {
    if (typeof window !== 'undefined') {
      try {
        localStorage.setItem(this.storageKey, JSON.stringify(this.configs));
      } catch (error) {
        console.error('Error saving API configs:', error);
      }
    }
  }

  addConfig(config: Omit<APIConfig, 'isActive'>) {
    const newConfig: APIConfig = {
      ...config,
      isActive: this.configs.length === 0 // Make active if it's the first config
    };
    
    this.configs.push(newConfig);
    if (newConfig.isActive) {
      this.activeConfig = newConfig;
    }
    this.saveConfigs();
  }

  updateConfig(configName: string, updates: Partial<Omit<APIConfig, 'isActive'>>) {
    const configIndex = this.configs.findIndex(c => c.name === configName);
    if (configIndex === -1) {
      throw new Error(`Configuration "${configName}" not found`);
    }

    const updatedConfig = {
      ...this.configs[configIndex],
      ...updates
    };

    if (!this.validateConfig(updatedConfig)) {
      throw new Error('Invalid configuration');
    }

    this.configs[configIndex] = updatedConfig;
    if (updatedConfig.isActive) {
      this.activeConfig = updatedConfig;
    }
    this.saveConfigs();
  }

  setActiveConfig(configName: string) {
    this.configs = this.configs.map(config => ({
      ...config,
      isActive: config.name === configName
    }));
    this.activeConfig = this.configs.find(c => c.name === configName) || null;
    this.saveConfigs();
  }

  getActiveConfig(): APIConfig | null {
    return this.activeConfig;
  }

  getAllConfigs(): APIConfig[] {
    return this.configs;
  }

  removeConfig(configName: string) {
    this.configs = this.configs.filter(config => config.name !== configName);
    if (this.activeConfig?.name === configName) {
      this.activeConfig = this.configs[0] || null;
      if (this.activeConfig) {
        this.activeConfig.isActive = true;
      }
    }
    this.saveConfigs();
  }

  validateConfig(config: Omit<APIConfig, 'isActive'>): boolean {
    try {
      new URL(config.baseUrl);
      return config.name.trim().length > 0;
    } catch {
      return false;
    }
  }
}

export const apiConfigManager = APIConfigManager.getInstance();
export type { APIConfig }; 