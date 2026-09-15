import {describe,expect,it,vi} from 'vitest'
import {sendChat} from './api'

describe ('sendChat',()=>{
    it('把message和session_id一起POST出去,并返回解析后的JSON',async()=>{
        const fetchMock = vi.fn().mockResolvedValue({
            ok:true,
            json:async() =>({session_id:7,reply:'收到'}),
        })
        vi.stubGlobal('fetch',fetchMock)

        const out = await sendChat(null,'在吗')

        expect(fetchMock).toHaveBeenCalledWith('/api/chat',expect.objectContaining({
            method:'POST',
        }))
        expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
            session_id:null,message:'在吗',
        })
        expect(out.reply).toBe('收到')
    })
})
