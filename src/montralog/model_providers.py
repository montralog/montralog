"""Small bounded model adapters. No tools, retries or arbitrary API parameters."""
import json
import os
import re
import urllib.parse
import urllib.request
from .outbound import open_request,endpoint,DestinationError

PROVIDERS=('ollama','openai','openai-compatible','anthropic','gemini')


def config():
    provider=os.getenv('MONTRALOG_AI_PROVIDER','ollama')
    model=os.getenv('MONTRALOG_AI_MODEL','qwen3:4b' if provider=='ollama' else '')
    base=os.getenv('MONTRALOG_AI_URL',{'ollama':'http://ollama:11434','openai':'https://api.openai.com/v1',
        'anthropic':'https://api.anthropic.com/v1','gemini':'https://generativelanguage.googleapis.com/v1beta'}.get(provider,'')).rstrip('/')
    if provider not in PROVIDERS or not re.fullmatch(r'[A-Za-z0-9_.:/-]{1,100}',model):raise ValueError('Configure a supported AI provider and model.')
    parsed,port=endpoint(base)
    if parsed.query:raise ValueError('AI base URL cannot contain query parameters.')
    local=provider=='ollama' and parsed.scheme=='http' and os.getenv('MONTRALOG_AI_LOCAL_HTTP','').lower()=='true' and parsed.hostname in ('ollama','localhost','127.0.0.1','::1','host.docker.internal')
    if parsed.scheme!='https' and not local:raise ValueError('AI providers require HTTPS; local Ollama requires explicit local HTTP opt-in.')
    key=os.getenv('MONTRALOG_AI_API_KEY','')
    if '\n' in key or '\r' in key or len(key)>8192:raise ValueError('Invalid provider key.')
    if provider!='ollama' and not key:raise ValueError('Configure the provider API key privately.')
    return {'provider':provider,'model':model,'base':base,'key':key,'local':local,'origin':(parsed.hostname,port)}


def generate(system,evidence):
    cfg=config();provider=cfg['provider'];model=cfg['model'];base=cfg['base']
    limit=1500
    messages=[{'role':'system','content':system},{'role':'user','content':evidence}]
    headers={'Content-Type':'application/json'}
    if provider=='ollama':
        url=base+'/api/chat';body={'model':model,'messages':messages,'stream':False,'think':False,'format':'json',
            'options':{'num_predict':limit,'num_ctx':8192,'temperature':0},'keep_alive':'5m'}
    elif provider=='openai':
        url=base+'/responses';headers['Authorization']='Bearer '+cfg['key']
        body={'model':model,'instructions':system,'input':evidence,'max_output_tokens':limit,'store':False,'text':{'format':{'type':'json_object'}}}
    elif provider=='openai-compatible':
        url=base+'/chat/completions';headers['Authorization']='Bearer '+cfg['key']
        body={'model':model,'messages':messages,'max_tokens':limit,'stream':False,'response_format':{'type':'json_object'}}
    elif provider=='anthropic':
        url=base+'/messages';headers.update({'x-api-key':cfg['key'],'anthropic-version':'2023-06-01'})
        body={'model':model,'system':system,'messages':[messages[1]],'max_tokens':limit}
    else:
        if not re.fullmatch('[A-Za-z0-9_.-]{1,100}',model):raise ValueError('Use a Gemini model ID without a URL/path.')
        url=base+'/models/'+model+':generateContent';headers['x-goog-api-key']=cfg['key']
        body={'systemInstruction':{'parts':[{'text':system}]},'contents':[{'role':'user','parts':[{'text':evidence}]}],
            'generationConfig':{'maxOutputTokens':limit,'responseMimeType':'application/json'}}
    request=urllib.request.Request(url,data=json.dumps(body,allow_nan=False).encode(),headers=headers)
    try:
        with open_request(request,timeout=240,private_origins=(f'{cfg["origin"][0]}:{cfg["origin"][1]}',) if cfg['local'] else (),
                          insecure_credential_origin=cfg['origin'] if cfg['local'] else None,require_private=cfg['local']) as response:
            raw=response.read(65537)
        if len(raw)>65536:raise ValueError('Model response too large')
        result=json.loads(raw)
        if provider=='ollama':
            if result.get('done') is not True or result.get('done_reason')=='length':raise ValueError('Incomplete model response')
            output=result['message']['content'];usage={'input':result.get('prompt_eval_count',0),'output':result.get('eval_count',0)}
        elif provider=='openai':
            if result.get('status')!='completed':raise ValueError('Incomplete model response')
            output=''.join(part.get('text','') for item in result.get('output',[]) if item.get('type')=='message' for part in item.get('content',[]) if part.get('type')=='output_text')
            usage=result.get('usage',{})
        elif provider=='openai-compatible':
            if result['choices'][0].get('finish_reason')!='stop':raise ValueError('Incomplete model response')
            output=result['choices'][0]['message']['content'];usage=result.get('usage',{})
        elif provider=='anthropic':
            if result.get('stop_reason')!='end_turn':raise ValueError('Incomplete model response')
            output=''.join(part.get('text','') for part in result['content'] if part.get('type')=='text');usage=result.get('usage',{})
        else:
            candidate=result['candidates'][0]
            if candidate.get('finishReason')!='STOP':raise ValueError('Incomplete model response')
            output=''.join(part.get('text','') for part in candidate['content']['parts']);usage=result.get('usageMetadata',{})
        parsed=json.loads(output)
        if not isinstance(parsed,dict):raise ValueError('Expected a JSON object')
        # Expose only bounded numeric token counters, never provider metadata/keys.
        usage={k:v for k,v in usage.items() if k in ('input','output','input_tokens','output_tokens','prompt_tokens','completion_tokens','total_tokens','promptTokenCount','candidatesTokenCount','totalTokenCount') and type(v) is int and 0<=v<=10000000}
        return parsed,usage
    except (OSError,ValueError,KeyError,TypeError,IndexError,DestinationError):
        raise ValueError('Model request failed or returned incomplete/invalid JSON; no action was executed.') from None
