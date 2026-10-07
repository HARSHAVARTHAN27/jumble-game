import fs from 'node:fs/promises'
import { Workbook } from '@oai/artifact-tool'

const teams = [
  ['Titans', [
    ['Ramesh Namperumal', ''],
    ['Kanishkaa', 'GIPL001'],
    ['Joni', 'GIPL004'],
    ['Eby', 'GIPL007'],
    ['Dhanushah', 'GIPL011'],
    ['Nagarjuna', 'GIPL015'],
    ['Shaik', 'GIPL018'],
    ['Babitha', 'GIPL021'],
    ['Siva', 'GIPL024'],
    ['Issac', 'GIPL027'],
    ['Ramesh Patil', 'GIPL031'],
    ['Sandeep Gowda', 'GIPL034'],
    ['Sravani Bethala', 'GIPL037'],
    ['Yashwardhan Singh Chouhan', 'GIPL043'],
  ]],
  ['Vibe Tribe', [
    ['Sanjai', 'GIPL002'],
    ['Anita', 'GIPL005'],
    ['Hemalatha', 'GIPL008'],
    ['Princy', 'GIPL013'],
    ['Raghul', 'GIPL016'],
    ['Jeffrey', 'GIPL019'],
    ['Sneha', 'GIPL022'],
    ['Sanjeeth', 'GIPL025'],
    ['Rayappa', 'GIPL028'],
    ['Rakesh', 'GIPL030'],
    ['Amruta', 'GIPL032'],
    ['Gnana sree', 'GIPL035'],
    ['Kailashnath Sharma', 'GIPL038'],
    ['Kavya B', 'GIPL044'],
  ]],
  ['Ctrl Alt Defeat', [
    ['Ram', ''],
    ['Malathy', 'GIPL003'],
    ['Dhanuja', 'GIPL006'],
    ['Sharmili', 'GIPL009'],
    ['Diyanesh', 'GIPL014'],
    ['Salini', 'GIPL017'],
    ['Giri', 'GIPL020'],
    ['Aditya', 'GIPL023'],
    ['Kowsalya', 'GIPL026'],
    ['Himanshu', 'GIPL029'],
    ['Ram Teja', 'GIPL033'],
    ['Mercy Flavia', 'GIPL036'],
    ['Srinath Chagaleti', 'GIPL039'],
    ['Pavan Shyam', 'GIPL040'],
    ['Saran', 'GIPL041'],
    ['Harshavarthan', 'GIPL042'],
  ]],
]
const rows = [['employee_name', 'employee_code', 'team'],
  ...teams.flatMap(([team, members]) => members.map(([name, code]) => [name, code, team]))]
const codes = rows.slice(1).map(row => row[1]).filter(Boolean)
if (rows.length !== 45 || new Set(codes).size !== 42) throw new Error('Roster count/unique code validation failed')
const workbook = Workbook.create()
const sheet = workbook.worksheets.add('Employees')
sheet.getRange('A1:C45').values = rows
sheet.getRange('A1:C45').format.font = { name: 'Arial', size: 11 }
sheet.getRange('A1:C1').format = { fill: '#5E3CAD', font: { name: 'Arial', size: 11, bold: true, color: '#FFFFFF' } }
sheet.getRange('A1:A45').format.columnWidth = 36
sheet.getRange('B1:B45').format.columnWidth = 20
sheet.getRange('C1:C45').format.columnWidth = 24
sheet.showGridLines = false
sheet.freezePanes.freezeRows(1)
workbook.recalculate()
const inspection = await workbook.inspect({ kind: 'table', range: 'Employees!A1:C5', include: 'values', tableMaxRows: 5, tableMaxCols: 3, maxChars: 1500 })
console.log(inspection.ndjson)
const preview = await workbook.render({ sheetName: 'Employees', range: 'A1:C16', scale: 1.5, format: 'png' })
await fs.writeFile(new URL('preview.png', import.meta.url), new Uint8Array(await preview.arrayBuffer()))
const escape = value => /[",\r\n]/.test(String(value ?? '')) ? '"' + String(value ?? '').replaceAll('"', '""') + '"' : String(value ?? '')
const csv = sheet.getRange('A1:C45').values.map(row => row.map(escape).join(',')).join('\r\n') + '\r\n'
await fs.writeFile(new URL('../backend/employees.csv', import.meta.url), csv, 'utf8')
console.log(JSON.stringify({ file: 'backend/employees.csv', total: 44, Titans: 14, 'Vibe Tribe': 14, 'Ctrl Alt Defeat': 16, missingCodes: ['Ramesh Namperumal', 'Ram'] }))
