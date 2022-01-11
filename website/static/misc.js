function throttleSearch(run, obj, key1 = 'loading', key2 = 'err', key3 = 'loading_timer', time = 10000) {
    return async function() {
        if (obj[key1] && obj[key1] !== 2) return
        obj[key1] = true
        obj[key3] = setTimeout(() => {
            obj[key1] = false
            obj[key2] = 'Search timed out.'
        }, time)

        try {
            await run()
            obj[key1] = false
        } catch(e) {
            obj[key1] = false
            obj[key2] = e
        } finally {
            clearTimeout(obj[key3])
        }
    }
}

function guidGenerator() {
    function S4() {
       return (((1+Math.random()) * 0x10000)|0).toString(16).substring(1)
    }
    return new Date().getTime().toString(36) + '-' + S4()
}

function cleanName(s) {
    s = s.replace(/\(/g, '').replace(/\)/g, '').replace(/:/g, '-').replace(/'/g, '')
    return s.replace(/ \/\/ /g, '--').replace(/, /g, '-').replace(/ /g, '-')
        .replace(/\//g, '-').toLowerCase()
}

function readFileAsync(file) {
    return new Promise((resolve, reject) => {
        let reader = new FileReader()
        reader.onload = () => {
            resolve(reader.result)
        }
        reader.onerror = reject
        reader.readAsDataURL(file)
    })
}

function shorten(str, num) {
     return str.length > num ? str.slice(0, num - 3) + '...' : str
}
