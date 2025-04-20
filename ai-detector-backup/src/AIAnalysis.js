const { OpenAIProvider, DeepSeekProvider, LlamaProvider } = require('./LLMProvider');

class AIAnalysis {
    constructor(provider, model, apiUrl) {
        switch (provider.toLowerCase()) {
            case 'openai':
                if (!process.env.OPENAI_API_KEY) {
                    throw new Error('OPENAI_API_KEY environment variable is required for OpenAI');
                }
                this.llm = new OpenAIProvider(process.env.OPENAI_API_KEY);
                break;

            case 'llama':
                this.llm = new LlamaProvider(model, apiUrl);
                break;

            case 'deepseek':
                if (!process.env.DEEPSEEK_API_KEY) {
                    throw new Error('DEEPSEEK_API_KEY environment variable is required for DeepSeek');
                }
                this.llm = new DeepSeekProvider(process.env.DEEPSEEK_API_KEY);
                break;

            default:
                throw new Error(`Unsupported LLM provider: ${provider}`);
        }
    }

    async analyzePodWithAI(podData) {
        try {
            // Create a comprehensive analysis prompt that considers all available data points
            const prompt = `Analyze this Kubernetes pod data to determine if it's running AI/ML workloads, with special attention to LLM (Language Model) applications.

Available Data Points:
${Object.keys(podData).map(key => `- ${key}`).join('\n')}

Consider the following indicators:

1. Running Processes:
- ML/AI framework processes (TensorFlow, PyTorch, etc.)
- Jupyter notebooks
- Python ML scripts
- Model serving processes
- GPU utilization

2. Installed Packages:
- ML/AI frameworks and libraries
- Data science packages
- LLM-specific packages (transformers, langchain, etc.)
- GPU support libraries

3. Environment Variables:
- API keys for AI services (OpenAI, Anthropic, etc.)
- ML framework configurations
- Model paths and settings
- GPU configurations

4. File System:
- ML model files (.h5, .pkl, .pt, etc.)
- Python/Jupyter notebooks
- Configuration files
- Requirements/dependency files

5. Network Connections:
- Connections to AI/ML services
- Model download endpoints
- API endpoints for AI services

Analyze the following pod data and provide a detailed assessment:
${JSON.stringify(podData, null, 2)}

IMPORTANT: Your response MUST be a valid JSON object with the following structure and nothing else:
{
    "is_ai": boolean,                    // Whether this pod is running AI/ML workloads
    "is_llm": boolean,                   // Whether this pod is specifically running LLM workloads
    "confidence": number,                // Confidence score (0-1)
    "detected_frameworks": string[],     // List of detected ML/AI frameworks
    "detected_services": string[],       // List of detected AI services being used
    "indicators": {                      // Detailed breakdown of indicators found
        "processes": string[],           // AI-related processes found
        "packages": string[],            // AI-related packages found
        "env_vars": string[],            // AI-related environment variables found
        "files": string[],               // AI-related files found
        "network": string[]              // AI-related network connections found
    },
    "risk_assessment": {
        "level": string,                 // "low", "medium", or "high"
        "factors": string[]              // List of risk factors identified
    },
    "analysis_details": string           // Detailed explanation of the analysis
}`;
            console.log('%%%%%%%%%%%Sending pod to AI analysis');
            const response = await this.llm.askWithAttachment(prompt, podData);
            
            if (!response.success) {
                throw new Error(response.error || 'Failed to analyze pod data');
            }

            // Remove code block markers and comments from the JSON string, but preserve URLs
            const cleanedJson = response.response
                .replace(/^```json\s*/, '') // Remove ```json prefix
                .replace(/\s*```$/, '')     // Remove ``` trailer
                .replace(/(?<!:)\/\/[^\n]*/g, '') // Remove single-line comments but preserve URLs (http:// etc)
                .replace(/\/\*[\s\S]*?\*\//g, ''); // Remove multi-line comments
            
            try {
                const parsedResponse = JSON.parse(cleanedJson);
                return parsedResponse;
            } catch (parseError) {
                console.error('Error parsing cleaned JSON:', parseError);
                console.log('Cleaned JSON string (length:', cleanedJson.length, '):', cleanedJson);
                throw new Error('Failed to parse AI analysis results after cleanup');
            }
        } catch (error) {
            console.error('Error in AI analysis:', error);
            return {
                is_ai: false,
                is_llm: false,
                confidence: 0,
                detected_frameworks: [],
                detected_services: [],
                indicators: {
                    processes: [],
                    packages: [],
                    env_vars: [],
                    files: [],
                    network: []
                },
                risk_assessment: {
                    level: 'low',
                    factors: []
                },
                analysis_details: `Error performing analysis: ${error.message}`
            };
        }
    }
}

module.exports = AIAnalysis; 