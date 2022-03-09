const card_tooltip = {
    props: ['id', 'name'],
    template: `
    <span class="card-tooltip">
        <a :href="'/cards/' + id" @mouseover="loadImage">
            <slot>[[ name ]]</slot>
        </a>
        <span class="tooltip-span">
            <img src="data:" :alt="name" ref="tooltipImg" />
        </span>
    </span>`,
    data() {
        return { loaded: false }
    },
    methods: {
        loadImage() {
            if (this.loaded) return
            this.loaded = true
            this.$refs.tooltipImg.setAttribute("src", "/cards/image/" + this.id)
        }
    }
}

function deck_sort(key, obj) {
    if (obj.current_sort_order[0] !== key)
        obj.current_sort_order = [key, !obj.sort_orders[key]]
    else
        obj.current_sort_order[1] = !obj.current_sort_order[1]
    obj.data.decks.sort((x, y) => {
        const a = x.sort_data[key]
        const b = y.sort_data[key]
        const check = a + 0 === a ? a - b : a.localeCompare(b)
        return obj.current_sort_order[1] ? check : -check
    })
}

const deck_list = {
    props: ['hide', 'data', 'format'],
    template: `
    <div v-if="data.partial_load" class="alert alert-info alert-dismissible fade show mt-1">
        <span>This competition has too many decks to fully load it. Only the best decks were loaded.</span>
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    <div id="deck-list">
        <table class="table table-striped" v-if="!data.loading && data.decks.length > 0">
            <thead>
                <tr>
                    <th>Colors</th>
                    <th @click="sort('name')"><a href="#">Name</a></th>
                    <th v-if="!int_hide.author" @click="sort('author')"><a href="#">Author</a></th>
                    <th v-if="!int_hide.archetype" @click="sort('archetype')"><a href="#">Archetype</a></th>
                    <th v-if="!int_hide.competition" @click="sort('competition')"><a href="#">Competition</a></th>
                    <th v-if="!int_hide.format" @click="sort('format')"><a href="#">Format</a></th>
                    <th @click="sort('record')"><a href="#">Record</a></th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="i in data.decks">
                    <td v-if="!i.deck.color_data">
                        <img :src="'/imagery/colors/' + i.deck.deck_id" alt="Deck's colors" />
                    </td>
                    <td v-else="">
                        <div class="fake-color-bar">
                            <div v-for="x, ind in i.deck.color_data" :style="'width: ' + (x * 100) + '%'"
                                :class="['fcb-' + x, 'fcbc-' + ind]"></div>
                        </div>
                    </td>
                    <td><a :href="'/decks/' + i.deck.deck_id">[[ shorten(i.deck.name, 50) ]]</a></td>
                    <td v-if="!int_hide.author">
                        <a :href="'/users/' + i.author.user_id">[[ i.author.nickname ]]</a>
                    </td>
                    <td v-if="!int_hide.archetype">
                        <a class="badge bg-primary text-decoration-none" :href="'/tags/' + i.tags[0].tag_id">
                            [[ i.tags[0].name ]]
                        </a>
                    </td>
                    <td v-if="!int_hide.competition">
                        <a :href="'/competitions/' + i.competition.competition_id">[[ i.competition.name ]]</a>
                    </td>
                    <td v-if="!int_hide.format"><a :href="'?format=' + i.deck.format">[[ i.format ]]</a></td>
                    <td>[[ i.deck.wins ]]-[[ i.deck.losses ]]<span v-if="i.ties">-[[ i.deck.ties ]]</span></td>
                </tr>
            </tbody>
        </table>
        <span class="text-warning" v-if="data.loading">Loading...</span>
        <span class="text-warning" v-if="!data.loading && data.decks.length === 0">No matches.</span>
    </div>
    `,
    data() {
        return {
            int_hide: {
                author: this.hide.indexOf('author') > -1,
                archetype: this.hide.indexOf('archetype') > -1,
                competition: this.hide.indexOf('competition') > -1,
                format: this.hide.indexOf('format') > -1 || (this.format && this.format !== '_all')
            },
            sort_orders: {record: 1},
            current_sort_order: ['none', 0],
            shorten: shorten
        }
    },
    methods: {
        sort: function(u) {deck_sort(u, this)}
    }
}

const popular_cards = {
    props: ['data'],
    template: `
    <div id="deck-list">
        <table class="table table-striped" v-if="!data.loading && data.popular_cards.length > 0">
            <thead>
                <tr>
                    <th @click="sort('name')"><a href="#">Card</a></th>
                    <th @click="sort('weight')"><a href="#">Weight</a></th>
                    <th @click="sort('record')"><a href="#">Record</a></th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="i in data.popular_cards">
                    <td><tooltip :id="i.card.card_id" :name="i.card.name"></tooltip></td>
                    <td>[[ i.weight ]]</td>
                    <td>[[ i.wins ]]-[[ i.losses ]]</td>
                </tr>
            </tbody>
        </table>
        <span class="text-warning" v-if="data.loading">Loading...</span>
        <span class="text-warning" v-if="!data.loading && data.popular_cards.length === 0">No matches.</span>
    </div>
    `,
    data() {
        return {
            sort_orders: {weight: 1, record: 1},
            current_sort_order: ['none', 0]
        }
    },
    methods: {
        sort: function(u) {deck_sort(u, this)}
    }
}
