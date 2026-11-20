
import { useMemo, useState } from 'react'
import {
    Search,
    Package,
    FileText,
    MapPin,
    Barcode,
    CalendarDays,
    X,
    BookOpen,
    Boxes,
} from 'lucide-react'
import {
    DEMO_PRODUCTS,
    DEMO_POLICIES,
} from '../../data/searchData'

type SearchFilter = 'all' | 'products' | 'policies'

export default function EmployeeSearch() {
    const [query, setQuery] = useState('')
    const [filter, setFilter] = useState<SearchFilter>('all')

    const normalizedQuery = query.trim().toLowerCase()

    const products = useMemo(() => {
        if (filter === 'policies') return []

        if (!normalizedQuery) return DEMO_PRODUCTS

        return DEMO_PRODUCTS.filter(product =>
            [
                product.name,
                product.sku,
                product.barcode,
                product.category,
                product.description,
                product.location,
                product.status,
            ].some(value => value.toLowerCase().includes(normalizedQuery)),
        )
    }, [normalizedQuery, filter])

    const policies = useMemo(() => {
        if (filter === 'products') return []

        if (!normalizedQuery) return DEMO_POLICIES

        return DEMO_POLICIES.filter(policy =>
            [
                policy.title,
                policy.category,
                policy.reference,
                policy.summary,
            ].some(value => value.toLowerCase().includes(normalizedQuery)),
        )
    }, [normalizedQuery, filter])

    const totalResults = products.length + policies.length

    const filters: { id: SearchFilter; label: string }[] = [
        { id: 'all', label: 'All results' },
        { id: 'products', label: 'Products' },
        { id: 'policies', label: 'Policies' },
    ]

    return (
        <div className="space-y-6">
            {/* Heading */}
            <div>
                <p className="text-sm font-medium text-blue-600">
                    Employee Workspace
                </p>
                <h1 className="mt-1 text-2xl font-bold text-slate-900">
                    Product & Policy Search
                </h1>
                <p className="mt-2 text-sm text-slate-500">
                    Find workplace products, inventory information and
                    operational policies in one place.
                </p>
            </div>

            {/* Search input */}
            <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:p-6">
                <label
                    htmlFor="employee-search"
                    className="mb-3 block text-sm font-semibold text-slate-800"
                >
                    What are you looking for?
                </label>

                <div className="flex items-center gap-3 rounded-xl border border-slate-300 bg-slate-50 px-4 py-3 transition focus-within:border-blue-500 focus-within:ring-2 focus-within:ring-blue-100">
                    <Search className="h-5 w-5 shrink-0 text-slate-400" />

                    <input
                        id="employee-search"
                        type="search"
                        value={query}
                        onChange={event => setQuery(event.target.value)}
                        placeholder="Search product, SKU, barcode or policy..."
                        className="min-w-0 flex-1 bg-transparent text-sm text-slate-900 outline-none placeholder:text-slate-400"
                    />

                    {query && (
                        <button
                            type="button"
                            onClick={() => setQuery('')}
                            className="rounded-lg p-1 text-slate-400 hover:bg-slate-200 hover:text-slate-700"
                            aria-label="Clear search"
                        >
                            <X size={17} />
                        </button>
                    )}
                </div>

                <div className="mt-4 flex flex-wrap gap-2">
                    {filters.map(item => (
                        <button
                            key={item.id}
                            type="button"
                            onClick={() => setFilter(item.id)}
                            className={`rounded-lg px-4 py-2 text-sm font-medium transition ${filter === item.id
                                    ? 'bg-blue-600 text-white shadow-sm'
                                    : 'border border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                                }`}
                        >
                            {item.label}
                        </button>
                    ))}
                </div>

                <p className="mt-4 text-xs text-slate-400">
                    Demo search covers product names, SKU codes, barcodes,
                    policy titles and policy references.
                </p>
            </section>

            {/* Result summary */}
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                    <h2 className="font-semibold text-slate-900">
                        Search results
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                        {normalizedQuery
                            ? `Results matching "${query.trim()}"`
                            : 'Browse the available demo records'}
                    </p>
                </div>

                <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
                    {totalResults} results
                </span>
            </div>

            {totalResults === 0 ? (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-14 text-center">
                    <Search className="mx-auto h-10 w-10 text-slate-300" />
                    <h3 className="mt-4 font-semibold text-slate-800">
                        No matching results
                    </h3>
                    <p className="mt-2 text-sm text-slate-500">
                        Try another product name, SKU, barcode or policy keyword.
                    </p>
                    <button
                        onClick={() => {
                            setQuery('')
                            setFilter('all')
                        }}
                        className="mt-4 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                    >
                        Clear search
                    </button>
                </div>
            ) : (
                <div className="space-y-8">
                    {/* Products */}
                    {products.length > 0 && (
                        <section>
                            <div className="mb-4 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div className="rounded-lg bg-blue-50 p-2 text-blue-600">
                                        <Package size={19} />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-slate-900">
                                            Products
                                        </h3>
                                        <p className="text-xs text-slate-500">
                                            Inventory and equipment records
                                        </p>
                                    </div>
                                </div>
                                <span className="text-xs font-medium text-slate-500">
                                    {products.length} found
                                </span>
                            </div>

                            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                                {products.map(product => (
                                    <article
                                        key={product.id}
                                        className="rounded-2xl border border-slate-200 bg-white p-5 transition hover:border-blue-200 hover:shadow-sm"
                                    >
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="flex min-w-0 items-start gap-3">
                                                <div className="rounded-xl bg-blue-50 p-3 text-blue-600">
                                                    <Boxes size={21} />
                                                </div>
                                                <div className="min-w-0">
                                                    <h4 className="font-semibold text-slate-900">
                                                        {product.name}
                                                    </h4>
                                                    <p className="mt-1 text-xs text-slate-500">
                                                        {product.category}
                                                    </p>
                                                </div>
                                            </div>

                                            <span
                                                className={`shrink-0 rounded-full px-2.5 py-1 text-[11px] font-semibold ${product.status === 'Available'
                                                        ? 'bg-green-50 text-green-700'
                                                        : product.status === 'Low Stock'
                                                            ? 'bg-amber-50 text-amber-700'
                                                            : 'bg-red-50 text-red-700'
                                                    }`}
                                            >
                                                {product.status}
                                            </span>
                                        </div>

                                        <p className="mt-4 text-sm leading-6 text-slate-600">
                                            {product.description}
                                        </p>

                                        <div className="mt-4 space-y-2 border-t border-slate-100 pt-4">
                                            <div className="flex items-center gap-2 text-xs text-slate-500">
                                                <Barcode size={14} />
                                                SKU: {product.sku}
                                            </div>
                                            <div className="flex items-center gap-2 text-xs text-slate-500">
                                                <Barcode size={14} />
                                                Barcode: {product.barcode}
                                            </div>
                                            <div className="flex items-center gap-2 text-xs text-slate-500">
                                                <MapPin size={14} />
                                                {product.location}
                                            </div>
                                        </div>
                                    </article>
                                ))}
                            </div>
                        </section>
                    )}

                    {/* Policies */}
                    {policies.length > 0 && (
                        <section>
                            <div className="mb-4 flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                    <div className="rounded-lg bg-purple-50 p-2 text-purple-600">
                                        <BookOpen size={19} />
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-slate-900">
                                            Policies & Procedures
                                        </h3>
                                        <p className="text-xs text-slate-500">
                                            Workplace guidance and references
                                        </p>
                                    </div>
                                </div>
                                <span className="text-xs font-medium text-slate-500">
                                    {policies.length} found
                                </span>
                            </div>

                            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                                {policies.map(policy => (
                                    <article
                                        key={policy.id}
                                        className="rounded-2xl border border-slate-200 bg-white p-5 transition hover:border-purple-200 hover:shadow-sm"
                                    >
                                        <div className="flex items-start gap-3">
                                            <div className="rounded-xl bg-purple-50 p-3 text-purple-600">
                                                <FileText size={21} />
                                            </div>
                                            <div className="min-w-0">
                                                <h4 className="font-semibold text-slate-900">
                                                    {policy.title}
                                                </h4>
                                                <p className="mt-1 text-xs text-purple-600">
                                                    {policy.category}
                                                </p>
                                            </div>
                                        </div>

                                        <p className="mt-4 text-sm leading-6 text-slate-600">
                                            {policy.summary}
                                        </p>

                                        <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-4 text-xs text-slate-500">
                                            <span className="flex items-center gap-1.5 font-medium">
                                                <FileText size={14} />
                                                {policy.reference}
                                            </span>
                                            <span className="flex items-center gap-1.5">
                                                <CalendarDays size={14} />
                                                Updated {policy.lastUpdated}
                                            </span>
                                        </div>
                                    </article>
                                ))}
                            </div>
                        </section>
                    )}
                </div>
            )}
        </div>
    )
}
