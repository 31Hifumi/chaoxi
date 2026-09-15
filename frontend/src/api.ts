export type ChatReply = {session_id: number;reply:string}

export async function sendChat(
    session_id:number | null,
    message:string,
):Promise<ChatReply>{
    const resp = await fetch('/api/chat',{
        method:'POST',
        headers:{'content-type':'application/json'},
        body:JSON.stringify({session_id,message}),
    })
    if (!resp.ok) throw new Error(`请求失败：${resp.status}`)
    return resp.json()
}