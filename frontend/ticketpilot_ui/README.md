# ticketpilot_ui

```bash
npm install
cp .env.example .env   # set VITE_API_BASE if the backend isn't on localhost:8000
npm run dev
```

Opens on `http://localhost:7102`.

## Pages

- `/` -- SubmitTicket (customer, no login)
- `/my-tickets` -- MyTickets (customer, no login)
- `/tickets/:ticketId` -- TicketDetail, with a Reopen button once resolved
- `/login` -- support-manager login
- `/approvals` -- ApprovalQueue (support manager, requires login)

Built the same way as the `brahmand_ui` reference: Vite + React 18 +
Redux Toolkit + antd + axios + react-router-dom, with
`src/utils/apiHelper.js` as the single axios instance (JWT attached via
request interceptor, 401s broadcast as a window event) and
`src/store/*Slice.js` + `store.js` for state.
