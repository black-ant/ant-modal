export namespace main {
	
	export class AIConfig {
	    id: string;
	    name: string;
	    provider: string;
	    baseUrl: string;
	    apiKey: string;
	    model: string;
	    temperature: number;
	    maxTokens: number;
	    isDefault: boolean;
	    // Go type: time
	    createdAt: any;
	    // Go type: time
	    updatedAt: any;
	
	    static createFrom(source: any = {}) {
	        return new AIConfig(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.id = source["id"];
	        this.name = source["name"];
	        this.provider = source["provider"];
	        this.baseUrl = source["baseUrl"];
	        this.apiKey = source["apiKey"];
	        this.model = source["model"];
	        this.temperature = source["temperature"];
	        this.maxTokens = source["maxTokens"];
	        this.isDefault = source["isDefault"];
	        this.createdAt = this.convertValues(source["createdAt"], null);
	        this.updatedAt = this.convertValues(source["updatedAt"], null);
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class CommandResult {
	    success: boolean;
	    output: string;
	    error: string;
	
	    static createFrom(source: any = {}) {
	        return new CommandResult(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.success = source["success"];
	        this.output = source["output"];
	        this.error = source["error"];
	    }
	}
	export class ExecutionLog {
	    id: string;
	    projectId: string;
	    projectName: string;
	    scriptName: string;
	    scriptPath: string;
	    scriptContent: string;
	    command: string;
	    variables: Record<string, string>;
	    startTime: number;
	    endTime: number;
	    status: string;
	    output: string;
	
	    static createFrom(source: any = {}) {
	        return new ExecutionLog(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.id = source["id"];
	        this.projectId = source["projectId"];
	        this.projectName = source["projectName"];
	        this.scriptName = source["scriptName"];
	        this.scriptPath = source["scriptPath"];
	        this.scriptContent = source["scriptContent"];
	        this.command = source["command"];
	        this.variables = source["variables"];
	        this.startTime = source["startTime"];
	        this.endTime = source["endTime"];
	        this.status = source["status"];
	        this.output = source["output"];
	    }
	}
	export class IDEConfig {
	    name: string;
	    path: string;
	    command: string;
	    icon: string;
	    enabled: boolean;
	    detected: boolean;
	
	    static createFrom(source: any = {}) {
	        return new IDEConfig(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.name = source["name"];
	        this.path = source["path"];
	        this.command = source["command"];
	        this.icon = source["icon"];
	        this.enabled = source["enabled"];
	        this.detected = source["detected"];
	    }
	}
	export class ModalApp {
	    id: string;
	    name: string;
	    appName: string;
	    description: string;
	    token: string;
	    tokenId: string;
	    tokenSecret: string;
	    workspace: string;
	    // Go type: time
	    createdAt: any;
	    // Go type: time
	    updatedAt: any;
	
	    static createFrom(source: any = {}) {
	        return new ModalApp(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.id = source["id"];
	        this.name = source["name"];
	        this.appName = source["appName"];
	        this.description = source["description"];
	        this.token = source["token"];
	        this.tokenId = source["tokenId"];
	        this.tokenSecret = source["tokenSecret"];
	        this.workspace = source["workspace"];
	        this.createdAt = this.convertValues(source["createdAt"], null);
	        this.updatedAt = this.convertValues(source["updatedAt"], null);
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}
	export class Script {
	    name: string;
	    path: string;
	    fullPath: string;
	    description: string;
	    order: number;
	
	    static createFrom(source: any = {}) {
	        return new Script(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.name = source["name"];
	        this.path = source["path"];
	        this.fullPath = source["fullPath"];
	        this.description = source["description"];
	        this.order = source["order"];
	    }
	}
	export class Project {
	    id: string;
	    name: string;
	    path: string;
	    description: string;
	    appId: string;
	    status: string;
	    scripts: Script[];
	    variables: Record<string, string>;
	    // Go type: time
	    createdAt: any;
	    // Go type: time
	    updatedAt: any;
	
	    static createFrom(source: any = {}) {
	        return new Project(source);
	    }
	
	    constructor(source: any = {}) {
	        if ('string' === typeof source) source = JSON.parse(source);
	        this.id = source["id"];
	        this.name = source["name"];
	        this.path = source["path"];
	        this.description = source["description"];
	        this.appId = source["appId"];
	        this.status = source["status"];
	        this.scripts = this.convertValues(source["scripts"], Script);
	        this.variables = source["variables"];
	        this.createdAt = this.convertValues(source["createdAt"], null);
	        this.updatedAt = this.convertValues(source["updatedAt"], null);
	    }
	
		convertValues(a: any, classs: any, asMap: boolean = false): any {
		    if (!a) {
		        return a;
		    }
		    if (a.slice && a.map) {
		        return (a as any[]).map(elem => this.convertValues(elem, classs));
		    } else if ("object" === typeof a) {
		        if (asMap) {
		            for (const key of Object.keys(a)) {
		                a[key] = new classs(a[key]);
		            }
		            return a;
		        }
		        return new classs(a);
		    }
		    return a;
		}
	}

}

