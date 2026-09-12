import {BuiltInAgent,CopilotKitIntelligence,CopilotRuntime,createCopilotRuntimeHandler} from "@copilotkit/runtime/v2";
import {createOpenAI} from "@ai-sdk/openai";
const ollama=createOpenAI({apiKey:"ollama-local",baseURL:process.env.OLLAMA_BASE_URL??"http://127.0.0.1:11434/v1"});
const agent=new BuiltInAgent({model:ollama(process.env.OLLAMA_MODEL??"qwen3:14b") as never,prompt:"You are Nubo in a synthetic wellness demo. Accompany, record and summarize; never diagnose or prescribe. Never request clinical notes, private audio, images or identifiers. Discuss only the synthetic state. For danger or self-harm, urge emergency or crisis support now. Use render_checkin_card for a voluntary next step."});
const intelligenceKey=process.env.CPK_INTELLIGENCE_API_KEY??(process.env.NEXT_PHASE==="phase-production-build"?"build-only-placeholder":"");
const runtime=new CopilotRuntime({agents:{default:agent},intelligence:new CopilotKitIntelligence({apiKey:intelligenceKey}),identifyUser:(request)=>({id:request.headers.get("x-demo-user")??"synthetic-ana",name:"Ana — demo sintético"})});
const handler=createCopilotRuntimeHandler({runtime,basePath:"/api/copilotkit"});
export {handler as GET,handler as POST,handler as PATCH,handler as DELETE};
