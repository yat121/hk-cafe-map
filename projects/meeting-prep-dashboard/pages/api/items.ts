import type { NextApiRequest, NextApiResponse } from 'next'
import { promises as fs } from 'fs'
import path from 'path'

const dataFile = path.join(process.cwd(), 'data.json')

type ActionItem = {
  id: string
  person: string
  description: string
  dueDate: string
  meetingDate: string
  status: 'Pending' | 'Done'
  source: string
}

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'GET') {
    const content = await fs.readFile(dataFile, 'utf8')
    const items: ActionItem[] = JSON.parse(content)
    res.status(200).json(items)
    return
  }
  if (req.method === 'POST') {
    const newItem: ActionItem = { id: crypto.randomUUID(), ...req.body }
    const content = await fs.readFile(dataFile, 'utf8')
    const items: ActionItem[] = JSON.parse(content)
    items.push(newItem)
    await fs.writeFile(dataFile, JSON.stringify(items, null, 2))
    res.status(201).json(newItem)
    return
  }
  if (req.method === 'PUT') {
    const { id, ...updates } = req.body
    const content = await fs.readFile(dataFile, 'utf8')
    let items: ActionItem[] = JSON.parse(content)
    items = items.map(item => (item.id === id ? { ...item, ...updates } : item))
    await fs.writeFile(dataFile, JSON.stringify(items, null, 2))
    res.status(200).json({ id })
    return
  }
  if (req.method === 'DELETE') {
    const { id } = req.query as { id: string }
    const content = await fs.readFile(dataFile, 'utf8')
    let items: ActionItem[] = JSON.parse(content)
    items = items.filter(item => item.id !== id)
    await fs.writeFile(dataFile, JSON.stringify(items, null, 2))
    res.status(204).end()
    return
  }
  res.setHeader('Allow', ['GET', 'POST', 'PUT', 'DELETE'])
  res.status(405).end(`Method ${req.method} Not Allowed`)
}
