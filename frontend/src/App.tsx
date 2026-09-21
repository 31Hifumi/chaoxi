import './App.css'
import {useState, type FormEvent} from "react";
import {sendChat} from "./api";

type Msg = {
    role: 'user' | 'assistant';
    content: string;
}


function App() {
    const [messages, setMessage] = useState<Msg[]>([])
    const [session_id, setSession_id] = useState<number | null>(null)
    const [draft, setDraft] = useState<string>("")
    const [sending, setSending] = useState<boolean>(false)

    async function handleSubmit(e: FormEvent) {
        e.preventDefault()
        const text = draft.trim()
        if (!text || sending) return
        setMessage((prev) => [...prev, {"role": "user", "content": text}])
        setDraft("")
        setSending(true)
        try {
            const data = await sendChat(session_id, text)
            setSession_id(data.session_id)
            setMessage((prev) => [...prev, {'role': 'assistant', 'content': data.reply}])
        } catch (err) {
            setMessage((prev) => [...prev, {'role': 'assistant', 'content': `出错了:${err}`}])
        } finally {
            setSending(false)
        }
    }

    return (
        <>
            <header>
                <h1>潮汐</h1>
                <h2>chaoxi</h2>
            </header>
            <main>
                {messages.map((m, i) => (<p key={i} className={m.role}>{m.content}</p>))}
                <form onSubmit={handleSubmit}>
                    <input
                        placeholder={"说点什么..."}
                        value={draft}
                        onChange={e => setDraft(e.target.value)}
                    />
                    <button type="submit" disabled={sending}>发送</button>
                </form>
            </main>
            <footer>
                <span>chaoxi</span>
                <a
                    className="beian"
                    href="https://beian.miit.gov.cn/"
                    target="_blank"
                    rel="noopener noreferrer"
                >
                    湘ICP备2026042157号-1
                </a>
            </footer>
        </>
    )
}

export default App
