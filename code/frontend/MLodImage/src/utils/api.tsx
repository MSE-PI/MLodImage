export const post = async (url: string, data: File) => {
    try {
        // const body = new FormData();
        // body.append('text', data);
        // for (const [key, value] of body.entries()) {
        //     console.log(key, value);
        // }
        const body = JSON.stringify({text: data});
        const response = await fetch("http://localhost:8000/process", {
            method: 'POST',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
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
