import { describe, it, expect, vi } from 'vitest';
import { screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ExtractionLineItemsEditor } from '../components/review/ExtractionLineItemsEditor';
import type { ExtractedLineItemData } from '../types/extraction';
import { renderWithProviders } from '../../../test/test-utils';

describe('ExtractionLineItemsEditor UI and Recalculations', () => {
  const initialItems: ExtractedLineItemData[] = [
    {
      line_number: 1,
      description: 'Stainless Steel Flange Bolt M10',
      manufacturer: 'FastenCorp',
      model: 'FC-M10',
      quantity: 50,
      unit: 'PCS',
      unit_price: 10.0,
      discount: 0,
      tax: 0,
      total: 500.0,
      specifications: [
        { name: 'Material', value: 'SS 316' },
      ],
      confidence_level: 0.95,
    },
  ];

  it('renders line item details and financial fields', () => {
    renderWithProviders(
      <ExtractionLineItemsEditor
        items={initialItems}
        currency="USD"
        onChange={vi.fn()}
      />
    );

    expect(screen.getByText(/extracted line items & pricing schedule/i)).toBeInTheDocument();
    expect(screen.getByDisplayValue('Stainless Steel Flange Bolt M10')).toBeInTheDocument();
    expect(screen.getByDisplayValue('50')).toBeInTheDocument();
    expect(screen.getByDisplayValue('10')).toBeInTheDocument();
  });

  it('automatically recalculates total when quantity or unit price is changed', () => {
    const handleChange = vi.fn();

    renderWithProviders(
      <ExtractionLineItemsEditor
        items={initialItems}
        currency="USD"
        onChange={handleChange}
      />
    );

    const priceInput = screen.getByDisplayValue('10');
    fireEvent.change(priceInput, { target: { value: '15' } });

    expect(handleChange).toHaveBeenCalled();
    const updatedList = handleChange.mock.calls[0][0];
    // 50 * 15 = 750.00
    expect(updatedList[0].total).toBe(750);
  });

  it('adds a new line item when Add Item button is clicked', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    renderWithProviders(
      <ExtractionLineItemsEditor
        items={initialItems}
        currency="USD"
        onChange={handleChange}
      />
    );

    const addBtn = screen.getByRole('button', { name: /add line item/i });
    await user.click(addBtn);

    expect(handleChange).toHaveBeenCalledTimes(1);
    const updatedList = handleChange.mock.calls[0][0];
    expect(updatedList).toHaveLength(2);
    expect(updatedList[1].description).toBe('New Line Item');
  });

  it('deletes an item when delete button is clicked', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    renderWithProviders(
      <ExtractionLineItemsEditor
        items={initialItems}
        currency="USD"
        onChange={handleChange}
      />
    );

    const deleteBtn = screen.getByTitle('Delete row');
    await user.click(deleteBtn);

    expect(handleChange).toHaveBeenCalledWith([]);
  });
});
