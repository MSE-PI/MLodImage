export const post = async (url: string, data: File) => {
    try {
        const body = new FormData();
        body.append('audio', data);
        const response = await fetch(url, {
            method: 'POST',
            mode: 'cors',
            body: body
        });
        console.log(response);
        if (response.status === 200) {
            return await response.json();
        }
        return false;
    } catch (error) {
        return error;
    }
}

export const get = async (url: string) => {
    return await fetch(url, {
        method: 'GET',
        mode: 'cors',
    })
}
