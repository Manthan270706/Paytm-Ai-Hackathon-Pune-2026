import { ReactElement, ReactNode } from 'react'
import { Button } from './Button'
import { Card } from './Card'
import { Input } from './Input'
import { ListRow } from './ListRow'
import { CaseStatus, StatusChip } from './StatusChip'

function assert(condition: boolean, message: string): void {
  if (!condition) {
    throw new Error(message)
  }
}

function asElement(node: ReactNode, label: string): ReactElement {
  if (!node || typeof node !== 'object' || !('props' in node)) {
    throw new Error(`${label} did not render an element`)
  }
  return node as ReactElement
}

function findByTestId(node: ReactNode, testId: string): ReactElement {
  if (!node || typeof node !== 'object' || !('props' in node)) {
    throw new Error(`missing ${testId}`)
  }
  const element = node as ReactElement<{ 'data-testid'?: string; children?: ReactNode }>
  if (element.props['data-testid'] === testId) {
    return element
  }
  const kids = element.props.children
  const list = Array.isArray(kids) ? kids : kids == null ? [] : [kids]
  for (const kid of list) {
    if (kid && typeof kid === 'object' && 'props' in kid) {
      try {
        return findByTestId(kid, testId)
      } catch {
        continue
      }
    }
  }
  throw new Error(`missing ${testId}`)
}

function classNameOf(node: ReactElement): string {
  return String((node.props as { className?: string }).className ?? '')
}

function assertTokens(node: ReactElement, token: string, label: string): void {
  const className = classNameOf(node)
  assert(className.includes(token), `${label} missing token ${token}`)
  assert(!/#(?:[0-9a-fA-F]{3,8})\b/.test(className), `${label} has a hard-coded hex colour`)
}

const HEX = /#(?:[0-9a-fA-F]{3,8})\b/

const button = asElement(Button({ children: 'Check my settlement', onClick: () => undefined }), 'Button')
assert(button.type === 'button', 'Button renders a native button')
assert(button.props.type === 'button', 'Button defaults to type=button so Enter and Space activate it')
assertTokens(button, 'bg-paytm-navy', 'Button')
assert(button.props.className.includes('min-h-12'), 'Button touch target uses the 48px scale')
assert(button.props.className.includes('focus-visible:ring-paytm-cyan'), 'Button focus ring uses the cyan token')

let clicks = 0
const liveButton = asElement(
  Button({
    children: 'Save',
    onClick: () => {
      clicks += 1
    },
  }),
  'Button',
)
liveButton.props.onClick?.()
assert(clicks === 1, 'Button onClick runs')
const disabled = asElement(Button({ children: 'Wait', disabled: true }), 'Button')
assert(disabled.props.disabled === true, 'Disabled button is not activatable')

const secondary = asElement(Button({ children: 'Back', variant: 'secondary' }), 'Button')
assertTokens(secondary, 'border-paytm-navy', 'Secondary button')
assert(!HEX.test(secondary.props.className), 'Secondary button has no hex')

const inputRoot = Input({
  id: 'settlement-query',
  label: 'What happened?',
  value: '',
  onChange: () => undefined,
})
const input = findByTestId(inputRoot, 'input')
assert(input.type === 'input', 'Input renders a native input')
assert(input.props.id === 'settlement-query', 'Input id is wired for the label')
assertTokens(input, 'bg-surface-subtle', 'Input')
assert(input.props.className.includes('min-h-12'), 'Input touch target uses the 48px scale')
assert(input.props.className.includes('text-base'), 'Input text is at least 16px')

let entered = 0
let typed = ''
const liveInput = findByTestId(
  Input({
    id: 'q',
    label: 'Search',
    value: 'old',
    onChange: (value) => {
      typed = value
    },
    onEnter: () => {
      entered += 1
    },
  }),
  'input',
)
;(liveInput.props.onKeyDown as (event: { key: string; shiftKey?: boolean }) => void)({ key: 'Enter' })
;(liveInput.props.onKeyDown as (event: { key: string; shiftKey?: boolean }) => void)({ key: 'a' })
assert(entered === 1, 'Input Enter key runs onEnter and other keys do not')
;(liveInput.props.onChange as (event: { target: { value: string } }) => void)({
  target: { value: '₹6,000' },
})
assert(typed === '₹6,000', 'Input onChange passes the field value')

const staticCard = asElement(Card({ title: 'Settlement', children: 'Expected ₹15,000' }), 'Card')
assert(staticCard.props.tabIndex === undefined, 'Static card is not a tab stop')
assertTokens(staticCard, 'bg-surface-card', 'Card')
assert(staticCard.props.className.includes('rounded-card'), 'Card uses the card radius token')
assert(staticCard.props.className.includes('shadow-sm'), 'Card uses the resting elevation token')

let activated = 0
const actionCard = asElement(
  Card({
    title: 'Open case',
    children: 'Checking',
    onActivate: () => {
      activated += 1
    },
  }),
  'Card',
)
assert(actionCard.props.role === 'button', 'Actionable card is a button for the keyboard')
assert(actionCard.props.tabIndex === 0, 'Actionable card is in tab order')
const onCardKey = actionCard.props.onKeyDown as (event: {
  key: string
  preventDefault: () => void
}) => void
onCardKey({ key: 'Enter', preventDefault: () => undefined })
onCardKey({ key: ' ', preventDefault: () => undefined })
onCardKey({ key: 'Escape', preventDefault: () => undefined })
assert(activated === 2, 'Card Enter and Space activate; other keys do not')

const row = asElement(
  ListRow({
    title: '12 Nov settlement',
    subtitle: 'Expected ₹15,000',
    amount: '₹6,000.00',
  }),
  'ListRow',
)
assertTokens(row, 'border-surface-divider', 'ListRow')
const amount = findByTestId(row, 'list-row-amount')
assert(amount.props.children === '₹6,000.00', 'ListRow shows the amount string')
assert(classNameOf(amount).includes('text-right'), 'ListRow amount is right-aligned')
assert(!HEX.test(classNameOf(amount)), 'ListRow amount has no hex')

let opened = 0
const actionRow = asElement(
  ListRow({
    title: 'Refund',
    amount: '₹1,200.00',
    onActivate: () => {
      opened += 1
    },
  }),
  'ListRow',
)
assert(actionRow.props.role === 'button', 'Actionable row is a button for the keyboard')
assert(actionRow.props.tabIndex === 0, 'Actionable row is in tab order')
assert(actionRow.props.className.includes('min-h-12'), 'ListRow touch target uses the 48px scale')
const onRowKey = actionRow.props.onKeyDown as (event: {
  key: string
  preventDefault: () => void
}) => void
onRowKey({ key: 'Enter', preventDefault: () => undefined })
onRowKey({ key: ' ', preventDefault: () => undefined })
assert(opened === 2, 'ListRow Enter and Space activate')

const statuses: CaseStatus[] = [
  'NEW',
  'IN_PROGRESS',
  'AWAITING_APPROVAL',
  'APPROVED',
  'VERIFYING',
  'RESOLVED',
  'REJECTED',
  'CANCELLED',
]
for (const status of statuses) {
  const chip = asElement(StatusChip({ status }), 'StatusChip')
  assert(chip.type === 'span', 'StatusChip renders a span')
  assert(chip.props.role === 'status', 'StatusChip exposes role=status')
  assert(chip.props.tabIndex === 0, 'StatusChip can be focused from the keyboard')
  assert(chip.props.className.includes('focus-visible:ring-paytm-cyan'), 'StatusChip focus ring uses the cyan token')
  assert(!HEX.test(chip.props.className), `StatusChip ${status} has no hex`)
  assert(typeof chip.props.children === 'string' && chip.props.children.length > 0, 'StatusChip has a visible label')
}
assertTokens(asElement(StatusChip({ status: 'NEW' }), 'StatusChip'), 'bg-status-new-bg', 'NEW chip')
assertTokens(asElement(StatusChip({ status: 'RESOLVED' }), 'StatusChip'), 'bg-status-progress-bg', 'RESOLVED chip')
assertTokens(asElement(StatusChip({ status: 'CANCELLED' }), 'StatusChip'), 'bg-surface-subtle', 'CANCELLED chip')

console.log('base-controls: 5 components passed')
