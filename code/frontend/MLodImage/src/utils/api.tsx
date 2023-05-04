export const post = async (url: string, data: File) => {
    try {
        const body = new FormData();
        body.append('audio', data);
        const response = await fetch(url, {
            method: 'POST',
            mode: 'cors',
            body: body
        });
        if (response.status === 200) {
            return await response.json();
        }
        return false;
    } catch (error) {
        return error;
    }
}

export const get = async (url: string) => {
    try {
        const result = await fetch(url, {
            method: 'GET',
            mode: 'cors',
        })
        if (result.status === 200) {
            return await result.json();
        }
        return false;
    } catch (error) {
        return {"status": "failed", "message": error};
    }
}

export const getResults = async (url: string) => {
    try {
        const result = await fetch(url, {
            method: 'GET',
            mode: 'cors',
        })
        if (result.status === 200) {
            return await result.blob();
        }
        return false;
    } catch (error) {
        return {"status": "failed", "message": error};
    }
}
